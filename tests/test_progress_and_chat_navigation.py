import ast
import re
import sys
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = ROOT / "addon" / "appModules" / "unigram.py"


def _class_ast(name):
	module = ast.parse(SOURCE_PATH.read_text(encoding="utf-8"))
	return next(node for node in module.body if isinstance(node, ast.ClassDef) and node.name == name)


def _load_app_method(name, namespace):
	method = next(
		node
		for node in _class_ast("AppModule").body
		if isinstance(node, ast.FunctionDef) and node.name == name
	)
	method.decorator_list = []
	exec(compile(ast.Module(body=[method], type_ignores=[]), str(SOURCE_PATH), "exec"), namespace)
	return namespace[name]


def _load_progress_tracker(monkeypatch, scheduled):
	class ScheduledCall:
		def __init__(self):
			self.stopped = False

		def Stop(self):
			self.stopped = True

	def call_later(delay, callback):
		call = ScheduledCall()
		scheduled.append((delay, callback, call))
		return call

	monkeypatch.setitem(sys.modules, "core", SimpleNamespace(callLater=call_later))
	namespace = {
		"Role": SimpleNamespace(LINK="link", BUTTON="button"),
		"api": SimpleNamespace(getFocusObject=lambda: None),
		"conf": SimpleNamespace(get=lambda key: "upload_download"),
		"log": SimpleNamespace(info=lambda *args: None, debug=lambda *args: None),
		"queueHandler": SimpleNamespace(
			eventQueue=object(),
			queueFunction=lambda *args: None,
		),
		"speech": SimpleNamespace(speakMessage=lambda text: None),
		"re": re,
		"_": lambda text: text,
	}
	exec(
		compile(ast.Module(body=[_class_ast("File_transfer_progress_tracking")], type_ignores=[]), str(SOURCE_PATH), "exec"),
		namespace,
	)
	return namespace["File_transfer_progress_tracking"]


def _load_chat_list_item():
	class ListItem:
		pass

	def script(**kwargs):
		return lambda function: function

	namespace = {
		"ListItem": ListItem,
		"script": script,
		"_": lambda text: text,
		"message": lambda text: None,
	}
	exec(
		compile(ast.Module(body=[_class_ast("ChatListItem")], type_ignores=[]), str(SOURCE_PATH), "exec"),
		namespace,
	)
	return namespace["ChatListItem"]


def test_progress_tracker_reuses_nvda_main_loop_without_timer_threads(monkeypatch):
	scheduled = []
	tracker = _load_progress_tracker(monkeypatch, scheduled)

	tracker.start()

	assert len(scheduled) == 1
	assert scheduled[0][0] == 350
	assert "Timer" not in {
		node.id
		for node in ast.walk(_class_ast("File_transfer_progress_tracking"))
		if isinstance(node, ast.Name)
	}

	_, callback, first_call = scheduled.pop()
	callback()

	assert len(scheduled) == 1
	assert not first_call.stopped
	tracker.stop()
	assert scheduled[0][2].stopped


def test_progress_tracker_stops_and_does_not_reschedule_at_100_percent(monkeypatch):
	scheduled = []
	tracker = _load_progress_tracker(monkeypatch, scheduled)
	button = object()
	tracker._is_unigram_object = classmethod(lambda cls, obj: True)
	tracker._is_in_foreground = classmethod(lambda cls, obj: True)
	tracker._is_transfer_button = classmethod(lambda cls, obj: True)
	tracker._read_fresh_value = classmethod(lambda cls, obj: "100%")
	tracker._get_key = classmethod(lambda cls, obj: ("button",))

	tracker.start()
	assert tracker.handle_progress(button, speak_first=True)

	assert not tracker.active
	assert not tracker._scheduled
	assert scheduled[0][2].stopped

	# A canceled callback may already be queued by some main-loop implementations.
	# Its generation token must prevent it from reviving the completed tracker.
	scheduled[0][1]()
	assert not tracker.active
	assert len(scheduled) == 1


def test_chat_mention_navigation_uses_the_stable_unigram_badge_glyph():
	chat_item = _load_chat_list_item()
	mention = SimpleNamespace(
		UIAAutomationId="UnreadMentionsLabel",
		name="\ueb00",
		children=[],
	)
	reaction = SimpleNamespace(
		UIAAutomationId="UnreadMentionsLabel",
		name="\ue9b6",
		children=[],
	)
	with_mention = SimpleNamespace(
		UIAAutomationId="ChatCell",
		children=[SimpleNamespace(UIAAutomationId="Grid", children=[mention])],
	)
	with_reaction = SimpleNamespace(UIAAutomationId="ChatCell", children=[reaction])

	assert chat_item._has_unread_mentions(with_mention)
	assert not chat_item._has_unread_mentions(with_reaction)


def test_chat_mention_navigation_skips_other_chats_in_both_directions():
	chat_item = _load_chat_list_item()

	def chat(glyph=None):
		children = []
		if glyph:
			children.append(SimpleNamespace(UIAAutomationId="UnreadMentionsLabel", name=glyph, children=[]))
		return SimpleNamespace(
			UIAAutomationId="ChatCell",
			children=children,
			next=None,
			previous=None,
			setFocus=lambda: None,
		)

	previous_mention = chat("\ueb00")
	previous_plain = chat()
	current = chat_item()
	current.UIAAutomationId = "ChatCell"
	current.children = []
	current.next = None
	current.previous = None
	next_plain = chat()
	next_mention = chat("\ueb00")
	items = [previous_mention, previous_plain, current, next_plain, next_mention]
	focused = []
	for index, item in enumerate(items):
		item.previous = items[index - 1] if index else None
		item.next = items[index + 1] if index + 1 < len(items) else None
		item.setFocus = lambda item=item: focused.append(item)

	assert current._move_to_chat_with_unread_mentions(True)
	assert focused.pop() is next_mention
	assert current._move_to_chat_with_unread_mentions(False)
	assert focused.pop() is previous_mention


def test_app_module_gain_focus_starts_one_shot_chat_list_focusing():
	scheduled = []
	instance = SimpleNamespace(
		isUnigramWindow=True,
		_autoFocusChatListAttempts=7,
		_scheduleAutoFocusChatList=lambda: scheduled.append(True),
	)
	method = _load_app_method("event_appModule_gainFocus", {})

	method(instance)

	assert instance._autoFocusChatListAttempts == 0
	assert scheduled == [True]


def test_auto_focus_is_scheduled_on_nvda_main_loop(monkeypatch):
	scheduled = []
	core = SimpleNamespace(
		callLater=lambda delay, callback, *args: scheduled.append((delay, callback, args))
	)
	monkeypatch.setitem(sys.modules, "core", core)
	callback = lambda generation: None
	instance = SimpleNamespace(
		_autoFocusChatListDone=False,
		_autoFocusChatListScheduled=False,
		_autoFocusChatListGeneration=4,
		_autoFocusChatListTick=callback,
	)
	namespace = {
		"conf": SimpleNamespace(get=lambda key: True),
		"log": SimpleNamespace(debug=lambda *args: None),
		"_AUTO_FOCUS_CHAT_LIST_DELAY_MS": 300,
	}
	method = _load_app_method("_scheduleAutoFocusChatList", namespace)

	method(instance)
	method(instance)

	assert instance._autoFocusChatListScheduled
	assert scheduled == [(300, callback, (4,))]


def test_auto_focus_is_not_scheduled_when_disabled(monkeypatch):
	scheduled = []
	monkeypatch.setitem(
		sys.modules,
		"core",
		SimpleNamespace(callLater=lambda *args: scheduled.append(args)),
	)
	instance = SimpleNamespace(
		_autoFocusChatListDone=False,
		_autoFocusChatListScheduled=False,
		_autoFocusChatListGeneration=4,
		_autoFocusChatListTick=lambda generation: None,
	)
	namespace = {
		"conf": SimpleNamespace(get=lambda key: False),
		"log": SimpleNamespace(debug=lambda *args: None),
		"_AUTO_FOCUS_CHAT_LIST_DELAY_MS": 300,
	}
	method = _load_app_method("_scheduleAutoFocusChatList", namespace)

	method(instance)

	assert not instance._autoFocusChatListScheduled
	assert scheduled == []


def test_auto_focus_waits_for_the_chat_list_then_completes():
	focus_calls = []
	retries = []
	instance = SimpleNamespace(
		_autoFocusChatListDone=False,
		_autoFocusChatListScheduled=True,
		_autoFocusChatListAttempts=0,
		_autoFocusChatListGeneration=2,
		script_toChatList=lambda gesture, arg=False: focus_calls.append(arg) or True,
		_scheduleAutoFocusChatList=lambda: retries.append(True),
	)
	focus = SimpleNamespace(
		appModule=instance,
		isInForeground=True,
		role="pane",
		parent=None,
	)
	namespace = {
		"api": SimpleNamespace(getFocusObject=lambda: focus),
		"conf": SimpleNamespace(get=lambda key: True),
		"Role": SimpleNamespace(LISTITEM="listItem"),
		"log": SimpleNamespace(debug=lambda *args: None),
		"_AUTO_FOCUS_CHAT_LIST_RETRY_LIMIT": 10,
	}
	method = _load_app_method("_autoFocusChatListTick", namespace)

	method(instance, 2)

	assert instance._autoFocusChatListDone
	assert not instance._autoFocusChatListScheduled
	assert focus_calls == [True]
	assert retries == []


def test_auto_focus_does_not_repeat_when_focus_is_already_in_chat_list():
	focus_calls = []
	instance = SimpleNamespace(
		_autoFocusChatListDone=False,
		_autoFocusChatListScheduled=True,
		_autoFocusChatListAttempts=0,
		_autoFocusChatListGeneration=1,
		script_toChatList=lambda gesture, arg=False: focus_calls.append(True),
		_scheduleAutoFocusChatList=lambda: None,
	)
	parent = SimpleNamespace(UIAAutomationId="ChatsList")
	focus = SimpleNamespace(
		appModule=instance,
		isInForeground=True,
		role="listItem",
		parent=parent,
	)
	namespace = {
		"api": SimpleNamespace(getFocusObject=lambda: focus),
		"conf": SimpleNamespace(get=lambda key: True),
		"Role": SimpleNamespace(LISTITEM="listItem"),
		"log": SimpleNamespace(debug=lambda *args: None),
		"_AUTO_FOCUS_CHAT_LIST_RETRY_LIMIT": 10,
	}
	method = _load_app_method("_autoFocusChatListTick", namespace)

	method(instance, 1)

	assert instance._autoFocusChatListDone
	assert focus_calls == []


def test_auto_focus_stops_retrying_at_the_limit():
	retries = []
	instance = SimpleNamespace(
		_autoFocusChatListDone=False,
		_autoFocusChatListScheduled=True,
		_autoFocusChatListAttempts=9,
		_autoFocusChatListGeneration=3,
		script_toChatList=lambda gesture, arg=False: False,
		_scheduleAutoFocusChatList=lambda: retries.append(True),
	)
	focus = SimpleNamespace(
		appModule=instance,
		isInForeground=True,
		role="pane",
		parent=None,
	)
	namespace = {
		"api": SimpleNamespace(getFocusObject=lambda: focus),
		"conf": SimpleNamespace(get=lambda key: True),
		"Role": SimpleNamespace(LISTITEM="listItem"),
		"log": SimpleNamespace(debug=lambda *args: None),
		"_AUTO_FOCUS_CHAT_LIST_RETRY_LIMIT": 10,
	}
	method = _load_app_method("_autoFocusChatListTick", namespace)

	method(instance, 3)

	assert not instance._autoFocusChatListDone
	assert instance._autoFocusChatListAttempts == 10
	assert retries == []


def test_auto_focus_checkbox_is_persisted_and_enabled_by_default():
	config_source = (ROOT / "addon" / "appModules" / "cnf.py").read_text(encoding="utf-8")
	settings_source = (
		ROOT / "addon" / "GlobalPlugins" / "UnigramPlus" / "__init__.py"
	).read_text(encoding="utf-8-sig")

	assert '"autoFocusChatList = boolean(default=True)"' in config_source
	assert 'conf.get("autoFocusChatList")' in settings_source
	assert 'conf.set("autoFocusChatList", self.autoFocusChatList.IsChecked())' in settings_source


def test_chat_list_items_receive_the_mention_navigation_overlay():
	app_module = _class_ast("AppModule")
	chooser = next(
		node
		for node in app_module.body
		if isinstance(node, ast.FunctionDef) and node.name == "chooseNVDAObjectOverlayClasses"
	)
	source = ast.unparse(chooser)

	assert "parent.UIAAutomationId == 'ChatsList'" in source
	assert "clsList.insert(0, ChatListItem)" in source
