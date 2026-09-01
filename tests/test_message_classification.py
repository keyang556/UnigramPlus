import ast
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = ROOT / "addon" / "appModules" / "unigram.py"
_UNSET = object()


class Node:
	def __init__(
		self,
		*,
		parent=None,
		role="listItem",
		automation_id="",
		class_name="",
		cached_class_name=_UNSET,
		name="",
		focusable=True,
	):
		self.parent = parent
		self.role = role
		self.UIAAutomationId = automation_id
		self.UIAClassName = class_name
		self.UIAElement = SimpleNamespace(
			cachedClassName=class_name if cached_class_name is _UNSET else cached_class_name
		)
		self.name = name
		self.isFocusable = focusable
		self.states = set()


def _source_module():
	return ast.parse(SOURCE_PATH.read_text(encoding="utf-8"))


def _load_members(names, namespace):
	members = [
		node
		for node in _source_module().body
		if isinstance(node, ast.FunctionDef) and node.name in names
	]
	exec(compile(ast.Module(body=members, type_ignores=[]), str(SOURCE_PATH), "exec"), namespace)
	return namespace


def _load_overlay_chooser(namespace):
	app_module = next(
		node for node in _source_module().body if isinstance(node, ast.ClassDef) and node.name == "AppModule"
	)
	chooser = next(
		node
		for node in app_module.body
		if isinstance(node, ast.FunctionDef) and node.name == "chooseNVDAObjectOverlayClasses"
	)
	chooser.decorator_list = []
	exec(compile(ast.Module(body=[chooser], type_ignores=[]), str(SOURCE_PATH), "exec"), namespace)
	return namespace["chooseNVDAObjectOverlayClasses"]


def _message_predicate():
	namespace = {"Role": SimpleNamespace(LISTITEM="listItem")}
	_load_members({"_find_ancestor_by_automation_id", "_is_message_list_item"}, namespace)
	return namespace["_is_message_list_item"]


def _chat_predicate():
	namespace = {"Role": SimpleNamespace(LISTITEM="listItem")}
	_load_members({"_find_ancestor_by_automation_id", "_is_chat_list_item"}, namespace)
	return namespace["_is_chat_list_item"]


def _overlay_classes_for(obj):
	message_overlay = type("Message_list_item", (), {})
	chat_overlay = type("ChatListItem", (), {})
	namespace = {
		"Role": SimpleNamespace(LISTITEM="listItem", EDITABLETEXT="editableText", BUTTON="button"),
		"State": SimpleNamespace(SELECTED="selected"),
		"Message_list_item": message_overlay,
		"ChatListItem": chat_overlay,
		"SettingsPanelListItem": type("SettingsPanelListItem", (), {}),
		"EditableText": type("EditableText", (), {}),
		"Audio_and_video_button": type("Audio_and_video_button", (), {}),
		"keywordsInMessages": {"en": ("seen", "not seen", "Sent at", "Received at")},
		"conf": SimpleNamespace(get=lambda key: "en" if key == "lang" else "normal"),
		"_WINDOW_SURFACE_AUTOMATION_IDS": frozenset(),
		"_is_chat_list_item": _chat_predicate(),
		"_is_message_list_item": _message_predicate(),
		"is_recording_button": lambda candidate: False,
	}
	chooser = _load_overlay_chooser(namespace)
	app = SimpleNamespace(
		isUnigramWindow=True,
		sender_message="unchanged",
		end_text="unchanged",
		_remember_messages_button=lambda candidate: None,
	)
	classes = []
	chooser(app, obj, classes)
	return classes, app, message_overlay, chat_overlay


def test_saved_messages_topics_with_received_or_sent_dates_are_not_messages():
	for name in (
		"某聊天室, 某訊息內容, 收到了 2026/8/31 下午 11:22",
		"某聊天室, 某訊息內容, 傳送於 2026/8/31 下午 11:22",
	):
		topic = Node(parent=Node(automation_id="ScrollingHost"), name=name)
		assert not _message_predicate()(topic)

		classes, app, message_overlay, _chat_overlay = _overlay_classes_for(topic)
		assert message_overlay not in classes
		assert app.sender_message == "unchanged"
		assert app.end_text == "unchanged"


def test_current_message_selector_and_toggle_button_receive_message_overlay():
	messages = Node(automation_id="Messages", role="list")
	for automation_id, class_name, parent in (
		("MessageSelector", "", messages),
		("", "MessageSelector", messages),
		("", "ToggleButton", messages),
	):
		message = Node(
			parent=parent,
			automation_id=automation_id,
			class_name=class_name,
			name="Message body, Received at 2026/08/31 23:22",
		)

		assert _message_predicate()(message)
		classes, app, message_overlay, _chat_overlay = _overlay_classes_for(message)
		assert message_overlay in classes
		assert app.sender_message == "received"


def test_legacy_message_marker_and_blank_service_messages_remain_messages():
	message = Node(parent=Node(), automation_id="Message_item", name="")

	assert _message_predicate()(message)
	classes, _app, message_overlay, _chat_overlay = _overlay_classes_for(message)
	assert message_overlay in classes


def test_empty_cached_uia_class_falls_back_to_the_live_message_class():
	messages = Node(automation_id="Messages", role="list")
	for cached_class_name, class_name in (("", "ToggleButton"), (None, "MessageSelector")):
		message = Node(
			parent=messages,
			class_name=class_name,
			cached_class_name=cached_class_name,
		)

		assert _message_predicate()(message)
		classes, _app, message_overlay, _chat_overlay = _overlay_classes_for(message)
		assert message_overlay in classes


def test_toggle_button_list_items_outside_messages_do_not_receive_message_overlay():
	for automation_id in ("CallsList", "SettingsList", "ScrollingHost"):
		control = Node(parent=Node(automation_id=automation_id), class_name="ToggleButton")

		assert not _message_predicate()(control)
		classes, _app, message_overlay, _chat_overlay = _overlay_classes_for(control)
		assert message_overlay not in classes


def test_chat_rows_with_message_like_summaries_keep_the_chat_overlay():
	chat = Node(
		parent=Node(automation_id="ChatsList"),
		name="Group, last message, Received at 2026/08/31 23:22",
	)

	assert not _message_predicate()(chat)
	classes, _app, message_overlay, chat_overlay = _overlay_classes_for(chat)
	assert message_overlay not in classes
	assert chat_overlay in classes


def test_message_overlay_does_not_override_the_provider_automation_id():
	message_class = next(
		node
		for node in _source_module().body
		if isinstance(node, ast.ClassDef) and node.name == "Message_list_item"
	)
	assert not any(
		isinstance(node, ast.Assign)
		and any(isinstance(target, ast.Name) and target.id == "UIAAutomationId" for target in node.targets)
		for node in message_class.body
	)
