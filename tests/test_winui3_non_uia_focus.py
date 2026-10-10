"""Objects that are not UIA must reach NVDA untouched.

The WinUI 3 Unigram focuses its window through IAccessible when switching back
to it, and NVDA creates InputComposition and CandidateItem objects while an IME
is in use. None of them has UIAAutomationId, and since 5.5.6 the focus handler
read it unguarded, so every one of those focus events logged an
AttributeError traceback.
"""

import ast
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = ROOT / "addon" / "appModules" / "unigram.py"


class UIA:
	"""Stands in for NVDAObjects.UIA.UIA."""


class NotUIA:
	"""Like NVDA's IAccessible window or InputComposition: no UIA properties."""

	def __init__(self, role, name=""):
		self.role = role
		self.name = name
		self.parent = None
		self.firstChild = None
		self.childCount = 0
		self.states = set()


class StrictApp:
	"""Fails as soon as the handler reaches anything past its guards."""

	def __init__(self, **attributes):
		self.__dict__.update(attributes)

	def __getattr__(self, name):
		raise AssertionError(f"the handler went on to {name}")


def _load_app_method(name, namespace):
	module = ast.parse(SOURCE_PATH.read_text(encoding="utf-8"))
	app = next(node for node in module.body if isinstance(node, ast.ClassDef) and node.name == "AppModule")
	method = next(node for node in app.body if isinstance(node, ast.FunctionDef) and node.name == name)
	method.decorator_list = []
	exec(compile(ast.Module(body=[method], type_ignores=[]), str(SOURCE_PATH), "exec"), namespace)
	return namespace[name]


def _namespace():
	def is_recording_button(obj):
		try:
			return obj.UIAAutomationId == "btnVoiceMessage"
		except Exception:
			return False

	return {
		"UIA": UIA,
		"is_recording_button": is_recording_button,
		"Role": SimpleNamespace(EDITABLETEXT="editableText", LISTITEM="listItem", PANE="pane"),
		"conf": SimpleNamespace(get=lambda key: True),
	}


def _calls():
	calls = []
	return calls, lambda: calls.append(True)


def test_focus_on_objects_that_are_not_uia_is_left_to_nvda():
	gain_focus = _load_app_method("event_gainFocus", _namespace())
	for obj in (
		NotUIA("pane"),  # the WinUI 3 window, reached through IAccessible
		NotUIA("editableText", "ㄊ"),  # an IME composition in the message field
		NotUIA("listItem", "他"),  # an IME candidate
	):
		calls, next_handler = _calls()
		gain_focus(StrictApp(isUnigramWindow=True), obj, next_handler)
		assert calls == [True], obj.role


def test_uia_focus_still_reaches_unigramplus():
	gain_focus = _load_app_method("event_gainFocus", _namespace())
	seen = []
	app = StrictApp(isUnigramWindow=True, _restore_focus_after_record_button=lambda obj: seen.append(obj) or True)
	focused = UIA()

	gain_focus(app, focused, lambda: None)

	assert seen == [focused]


def test_telegram_desktop_without_its_add_on_skips_unigrams_focus_handling():
	gain_focus = _load_app_method("event_gainFocus", _namespace())
	calls, next_handler = _calls()

	gain_focus(StrictApp(isUnigramWindow=False, _fallbackAppModule=None), UIA(), next_handler)

	assert calls == [True]


def test_show_name_and_hide_events_tolerate_objects_that_are_not_uia():
	namespace = _namespace()
	for name in ("event_show", "event_nameChange", "event_hide"):
		handler = _load_app_method(name, namespace)
		app = StrictApp(
			isUnigramWindow=True,
			_remember_messages_button=lambda obj: False,
			_voiceRecordingButton=None,
		)
		calls, next_handler = _calls()
		handler(app, NotUIA("pane"), next_handler)
		assert calls == [True], name


def test_overlay_selection_leaves_objects_that_are_not_uia_alone():
	"""NVDA builds these objects too, so overlay selection must not raise on them."""
	choose = _load_app_method("chooseNVDAObjectOverlayClasses", _namespace())
	cls_list = ["IAccessible"]

	choose(StrictApp(isUnigramWindow=True), NotUIA("editableText"), cls_list)

	assert cls_list == ["IAccessible"]
