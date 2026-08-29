import ast
import sys
import types
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).parents[1]
SOURCE_PATH = ROOT / "addon" / "GlobalPlugins" / "UnigramPlus" / "__init__.py"

# The real values, so composing them is checked rather than assumed.
WX_OK = 4
WX_ICON_INFORMATION = 2048


def _load_plugin_functions(names, namespace):
	"""Execute the named module-level functions without importing NVDA."""
	module = ast.parse(SOURCE_PATH.read_text(encoding="utf-8-sig"))
	members = [
		node
		for node in module.body
		if isinstance(node, ast.FunctionDef) and node.name in names
	]
	assert {node.name for node in members} == set(names), "missing functions in plugin source"
	exec(compile(ast.Module(body=members, type_ignores=[]), str(SOURCE_PATH), "exec"), namespace)
	return namespace


def _namespace(message_box_calls):
	# `gui` here is the module global the fallback branch calls; the `gui` entry in
	# sys.modules separately decides whether `from gui.message import ...` resolves.
	return {
		"gui": SimpleNamespace(messageBox=lambda *args: message_box_calls.append(args)),
		"wx": SimpleNamespace(OK=WX_OK, ICON_INFORMATION=WX_ICON_INFORMATION),
		"_": lambda text: text,
	}


def _install_modern_gui(monkeypatch, alert_calls):
	monkeypatch.setitem(sys.modules, "gui", types.ModuleType("gui"))
	message_module = types.ModuleType("gui.message")
	message_module.MessageDialog = SimpleNamespace(
		alert=lambda *args, **kwargs: alert_calls.append((args, kwargs))
	)
	monkeypatch.setitem(sys.modules, "gui.message", message_module)


def _install_legacy_gui(monkeypatch):
	# A plain module is not a package, so `from gui.message import ...` raises
	# ModuleNotFoundError, exactly as on NVDA versions before 2025.1.
	monkeypatch.setitem(sys.modules, "gui", types.ModuleType("gui"))
	monkeypatch.delitem(sys.modules, "gui.message", raising=False)


def test_alert_dialog_uses_message_dialog_on_nvda_2025_1_and_later(monkeypatch):
	alert_calls = []
	message_box_calls = []
	_install_modern_gui(monkeypatch, alert_calls)
	namespace = _load_plugin_functions({"_alert_dialog"}, _namespace(message_box_calls))

	namespace["_alert_dialog"]("Body text", "Dialog title")

	assert alert_calls == [(("Body text", "Dialog title"), {})]
	# The deprecated call must not also run, or the user sees two dialogs.
	assert message_box_calls == []


def test_alert_dialog_falls_back_to_message_box_on_older_nvda(monkeypatch):
	message_box_calls = []
	_install_legacy_gui(monkeypatch)
	namespace = _load_plugin_functions({"_alert_dialog"}, _namespace(message_box_calls))

	namespace["_alert_dialog"]("Body text", "Dialog title")

	assert message_box_calls == [("Body text", "Dialog title", WX_OK | WX_ICON_INFORMATION)]


def test_alert_dialog_does_not_swallow_failures_from_the_modern_dialog(monkeypatch):
	"""Only a missing gui.message may trigger the fallback."""
	message_box_calls = []
	monkeypatch.setitem(sys.modules, "gui", types.ModuleType("gui"))
	message_module = types.ModuleType("gui.message")

	def explode(*args, **kwargs):
		raise RuntimeError("wx failed")

	message_module.MessageDialog = SimpleNamespace(alert=explode)
	monkeypatch.setitem(sys.modules, "gui.message", message_module)
	namespace = _load_plugin_functions({"_alert_dialog"}, _namespace(message_box_calls))

	try:
		namespace["_alert_dialog"]("Body text", "Dialog title")
	except RuntimeError:
		pass
	else:
		raise AssertionError("a failing MessageDialog.alert should not be silently retried")
	assert message_box_calls == []


def test_no_updates_dialog_passes_the_translated_text_and_title(monkeypatch):
	alert_calls = []
	_install_modern_gui(monkeypatch, alert_calls)
	namespace = _load_plugin_functions({"_alert_dialog", "no_updates_dialog"}, _namespace([]))

	namespace["no_updates_dialog"]()

	assert alert_calls == [(("No updates available", "UnigramPlus update"), {})]


def test_no_updates_dialog_still_reaches_the_user_on_older_nvda(monkeypatch):
	message_box_calls = []
	_install_legacy_gui(monkeypatch)
	namespace = _load_plugin_functions(
		{"_alert_dialog", "no_updates_dialog"}, _namespace(message_box_calls)
	)

	namespace["no_updates_dialog"]()

	assert message_box_calls == [
		("No updates available", "UnigramPlus update", WX_OK | WX_ICON_INFORMATION)
	]


def _called_names(node):
	"""Every dotted call target inside an AST subtree, e.g. "gui.messageBox"."""
	names = set()
	for child in ast.walk(node):
		if not isinstance(child, ast.Call):
			continue
		func = child.func
		if isinstance(func, ast.Name):
			names.add(func.id)
		elif isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
			names.add("%s.%s" % (func.value.id, func.attr))
	return names


def test_the_deprecated_message_box_only_survives_inside_the_fallback():
	module = ast.parse(SOURCE_PATH.read_text(encoding="utf-8-sig"))
	holders = [
		node.name
		for node in ast.walk(module)
		if isinstance(node, ast.FunctionDef) and "gui.messageBox" in _called_names(node)
	]

	assert holders == ["_alert_dialog"], "gui.messageBox is deprecated outside the fallback"


def test_the_incompatible_bundle_warning_routes_through_the_compatibility_helper():
	module = ast.parse(SOURCE_PATH.read_text(encoding="utf-8-sig"))
	setup_update = next(
		node
		for node in ast.walk(module)
		if isinstance(node, ast.FunctionDef) and node.name == "setup_update"
	)
	warning = "The new version of UnigramPlus is not compatible with this version of NVDA. Please update NVDA first."
	strings = {
		child.value for child in ast.walk(setup_update) if isinstance(child, ast.Constant) and isinstance(child.value, str)
	}

	assert warning in strings, "the incompatible-bundle warning moved"
	assert "_alert_dialog" in _called_names(setup_update)


def test_settings_dialog_prefers_the_public_popup_api():
	source = SOURCE_PATH.read_text(encoding="utf-8-sig")

	# popupSettingsDialog is public since NVDA 2023.2; the underscore name only
	# survives as a fallback, never as the first choice.
	assert 'getattr(gui.mainFrame, "popupSettingsDialog", None)' in source
	assert "wx.CallAfter(popup," in source
	assert "wx.CallAfter(gui.mainFrame._popupSettingsDialog" not in source
