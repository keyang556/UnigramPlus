import ast
import sys
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).parents[1]
SOURCE_PATH = ROOT / "addon" / "appModules" / "unigram.py"


class Node:
	def __init__(
		self,
		name="",
		children=None,
		role=None,
		parent=None,
		automation_id="",
		class_name="",
		focusable=True,
	):
		self.name = name
		self.children = children or []
		self.role = role
		self.parent = parent
		self.UIAAutomationId = automation_id
		self.UIAClassName = class_name
		self.isFocusable = focusable
		self.states = set()
		self.next = None
		self.previous = None
		self.actions = 0

	@property
	def childCount(self):
		return len(self.children)

	def doAction(self):
		self.actions += 1

	@property
	def lastChild(self):
		return self.children[-1] if self.children else None


def _load_module_members(names, namespace):
	module = ast.parse(SOURCE_PATH.read_text(encoding="utf-8"))
	members = []
	for node in module.body:
		if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in names:
			if isinstance(node, ast.FunctionDef):
				node.decorator_list = []
			members.append(node)
	exec(compile(ast.Module(body=members, type_ignores=[]), str(SOURCE_PATH), "exec"), namespace)
	return namespace


def _load_app_method(name, namespace):
	module = ast.parse(SOURCE_PATH.read_text(encoding="utf-8"))
	app_module = next(
		node for node in module.body if isinstance(node, ast.ClassDef) and node.name == "AppModule"
	)
	method = next(node for node in app_module.body if isinstance(node, ast.FunctionDef) and node.name == name)
	method.decorator_list = []
	exec(compile(ast.Module(body=[method], type_ignores=[]), str(SOURCE_PATH), "exec"), namespace)
	return namespace[name]


def test_context_menu_icon_matching_handles_unigram_12_9_wrappers_and_cycles():
	namespace = _load_module_members(
		{"_walk_bounded_descendants", "_menu_item_has_icon"},
		{},
	)
	icon = Node("\ue74d")
	wrapper = Node(children=[Node(children=[icon])])
	icon.children = [wrapper]

	assert namespace["_menu_item_has_icon"](wrapper, "\ue74d")
	assert not namespace["_menu_item_has_icon"](wrapper, "\ue8b2")


def test_context_menu_deletion_still_activates_a_nested_delete_item():
	namespace = _load_module_members(
		{"_walk_bounded_descendants", "_menu_item_has_icon"},
		{},
	)
	role = SimpleNamespace(MENUITEM="menuItem", CHECKBOX="checkBox", BUTTON="button")
	delete_item = Node(children=[Node(children=[Node("\ue74d")])])
	other_item = Node(children=[Node(children=[Node("\ue8b2")])])
	menu = Node(children=[other_item, delete_item])
	focus = Node(role=role.MENUITEM, parent=menu)
	cancelled = []
	namespace.update(
		{
			"Role": role,
			"State": SimpleNamespace(CHECKED="checked"),
			"conf": SimpleNamespace(get=lambda key: False),
			"speech": SimpleNamespace(cancelSpeech=lambda: cancelled.append(True)),
			"icons_from_context_menu": {"delete": "\ue74d"},
		}
	)
	method = _load_app_method("deleteMessageAndChat", namespace)
	instance = SimpleNamespace(isDelete={"state": 0})

	method(instance, focus)

	assert cancelled == [True]
	assert delete_item.actions == 1
	assert other_item.actions == 0
	assert instance.isDelete["state"] == 1


def test_shift_delete_uses_unigrams_native_delete_for_messages():
	sent = []
	scheduled = []
	focus = Node(parent=Node(role="group"))
	namespace = {
		"api": SimpleNamespace(getFocusObject=lambda: focus),
		"Role": SimpleNamespace(LISTITEM="listItem"),
		"conf": SimpleNamespace(get=lambda key: False),
		"core": SimpleNamespace(callLater=lambda *args: scheduled.append(args)),
		"_": lambda text: text,
	}
	method = _load_app_method("startDeleteMessage", namespace)
	instance = SimpleNamespace(
		is_message_object=lambda obj: True,
		keys={
			"delete": SimpleNamespace(send=lambda: sent.append("delete")),
			"Applications": SimpleNamespace(send=lambda: sent.append("applications")),
		},
		_expire_native_delete=lambda pending: None,
	)

	assert method(instance, True, True)
	assert sent == ["delete"]
	assert instance.isDelete["state"] == 1
	assert instance.isDelete["isCompleteDeletion"] is True
	assert len(scheduled) == 1
	assert scheduled[0][0] == 20000
	assert scheduled[0][2] is instance.isDelete


def test_native_delete_preserves_the_confirmation_dialog_setting():
	sent = []
	focus = Node(parent=Node(role="group"))
	namespace = {
		"api": SimpleNamespace(getFocusObject=lambda: focus),
		"Role": SimpleNamespace(LISTITEM="listItem"),
		"conf": SimpleNamespace(get=lambda key: True),
		"core": SimpleNamespace(
			callLater=lambda *args: (_ for _ in ()).throw(
				AssertionError("confirmed deletion must not schedule automatic activation")
			),
		),
		"_": lambda text: text,
	}
	method = _load_app_method("startDeleteMessage", namespace)
	instance = SimpleNamespace(
		is_message_object=lambda obj: True,
		keys={
			"delete": SimpleNamespace(send=lambda: sent.append("delete")),
			"Applications": SimpleNamespace(send=lambda: sent.append("applications")),
		},
		_expire_native_delete=lambda pending: None,
	)

	assert method(instance, True, True)
	assert sent == ["delete"]
	assert instance.isDelete is False


def test_shift_delete_keeps_context_menu_fallback_for_chat_rows():
	sent = []
	chat_list = Node(automation_id="ChatsList")
	focus = Node(children=[Node(), Node("ordinary chat")], parent=chat_list)
	namespace = {
		"api": SimpleNamespace(getFocusObject=lambda: focus),
		"Role": SimpleNamespace(LISTITEM="listItem"),
		"conf": SimpleNamespace(get=lambda key: False),
		"_": lambda text: text,
	}
	method = _load_app_method("startDeleteMessage", namespace)
	instance = SimpleNamespace(
		is_message_object=lambda obj: False,
		keys={
			"delete": SimpleNamespace(send=lambda: sent.append("delete")),
			"Applications": SimpleNamespace(send=lambda: sent.append("applications")),
		},
	)

	assert method(instance, True, True)
	assert sent == ["applications"]
	assert instance.isDelete["state"] == 0


def test_native_delete_activates_the_focused_primary_button_without_walking_the_popup():
	class UnexpectedAdjacentTarget:
		@property
		def location(self):
			raise AssertionError("native deletion must not inspect cached adjacent rows")

	role = SimpleNamespace(MENUITEM="menuItem", CHECKBOX="checkBox", BUTTON="button")
	state = SimpleNamespace(CHECKED="checked")
	primary = Node(role=role.BUTTON, automation_id="PrimaryButton")
	namespace = {
		"Role": role,
		"State": state,
		"conf": SimpleNamespace(get=lambda key: False),
		"speech": SimpleNamespace(cancelSpeech=lambda: None),
	}
	method = _load_app_method("deleteMessageAndChat", namespace)
	instance = SimpleNamespace(
		isDelete={
			"state": 1,
			"isCompleteDeletion": True,
			"elements": [UnexpectedAdjacentTarget()],
			"list": "other",
			"nativeDelete": True,
		},
	)

	assert method(instance, primary)

	assert primary.actions == 1
	assert instance.isDelete["state"] == 2
	assert "_find_deletion_primary_button" not in SOURCE_PATH.read_text(encoding="utf-8")


def test_native_delete_ignores_unrelated_buttons_while_the_popup_is_loading():
	role = SimpleNamespace(MENUITEM="menuItem", CHECKBOX="checkBox", BUTTON="button")
	cancelled = []
	namespace = {
		"Role": role,
		"State": SimpleNamespace(CHECKED="checked"),
		"conf": SimpleNamespace(get=lambda key: False),
		"speech": SimpleNamespace(cancelSpeech=lambda: cancelled.append(True)),
	}
	method = _load_app_method("deleteMessageAndChat", namespace)
	pending = {
		"state": 1,
		"isCompleteDeletion": True,
		"elements": [],
		"list": "messages",
		"nativeDelete": True,
	}
	instance = SimpleNamespace(isDelete=pending)

	for automation_id in ("CalendarButton", "Attach", "SecondaryButton", ""):
		button = Node(role=role.BUTTON, automation_id=automation_id)
		assert not method(instance, button)
		assert button.actions == 0

	assert instance.isDelete is pending
	assert pending["state"] == 1
	assert cancelled == []


def test_native_delete_checkbox_is_only_toggled_when_delete_for_everyone_is_unchecked():
	role = SimpleNamespace(MENUITEM="menuItem", CHECKBOX="checkBox", BUTTON="button")
	state = SimpleNamespace(CHECKED="checked")
	namespace = {
		"Role": role,
		"State": state,
		"conf": SimpleNamespace(get=lambda key: False),
		"speech": SimpleNamespace(cancelSpeech=lambda: None),
	}
	method = _load_app_method("deleteMessageAndChat", namespace)
	pending = {
		"state": 1,
		"isCompleteDeletion": True,
		"elements": [],
		"list": "messages",
		"nativeDelete": True,
	}
	instance = SimpleNamespace(isDelete=pending)
	checkbox = Node(role=role.CHECKBOX, automation_id="RevokeCheck")

	assert method(instance, checkbox)
	assert checkbox.actions == 1
	assert pending["state"] == 1
	checkbox.states.add(state.CHECKED)
	assert method(instance, checkbox)
	assert checkbox.actions == 1
	assert pending["state"] == 1


def test_native_delete_timeout_only_clears_the_request_that_scheduled_it():
	method = _load_app_method("_expire_native_delete", {})
	first = {"state": 1}
	second = {"state": 1}
	instance = SimpleNamespace(isDelete=second)

	method(instance, first)
	assert instance.isDelete is second
	method(instance, second)
	assert instance.isDelete is False


def test_context_menu_delete_keeps_constant_time_checkbox_template_path():
	role = SimpleNamespace(MENUITEM="menuItem", CHECKBOX="checkBox", BUTTON="button")
	state = SimpleNamespace(CHECKED="checked")
	checkbox = Node(role=role.CHECKBOX, automation_id="RevokeCheck")
	primary = Node(role=role.BUTTON, automation_id="PrimaryButton")
	last = Node(role=role.BUTTON)
	last.previous = primary
	checkbox.parent = Node(children=[checkbox, primary, last])
	namespace = {
		"Role": role,
		"State": state,
		"conf": SimpleNamespace(get=lambda key: False),
		"speech": SimpleNamespace(cancelSpeech=lambda: None),
	}
	method = _load_app_method("deleteMessageAndChat", namespace)
	instance = SimpleNamespace(
		isDelete={
			"state": 1,
			"isCompleteDeletion": True,
			"elements": [],
			"list": "other",
			"nativeDelete": False,
		},
	)

	method(instance, checkbox)

	assert checkbox.actions == 1
	assert primary.actions == 1
	assert instance.isDelete["state"] == 2


def test_unigram_12_9_inline_button_label_is_recovered_without_the_icon_glyph(monkeypatch):
	namespace = _load_module_members(
		{"_clean_inline_button_text", "_inline_button_descendant_text"},
		{},
	)
	requested_lengths = []

	class TextPattern:
		DocumentRange = SimpleNamespace(GetText=lambda length: "\ue9b7 Open website")

		def QueryInterface(self, interface):
			assert interface == "textPatternInterface"
			return self

	class RawElement:
		def __init__(self, class_name="", automation_id="", children=None, text=""):
			self.class_name = class_name
			self.automation_id = automation_id
			self.children = children or []
			self.text = text

		def GetCachedPattern(self, pattern_id):
			assert pattern_id == "textPattern"
			pattern = TextPattern()
			pattern.DocumentRange = SimpleNamespace(
				GetText=lambda length: requested_lengths.append(length) or self.text,
			)
			return pattern

		def GetCachedPropertyValueEx(self, property_id, ignore_default):
			assert ignore_default is True
			return {
				"class": self.class_name,
				"automationId": self.automation_id,
				"name": "",
			}.get(property_id, "")

	class RawWalker:
		@staticmethod
		def GetFirstChildElementBuildCache(element, cache_request):
			assert cache_request == "baseCache"
			return element.children[0] if element.children else None

	# Raw UIA flattens the template peers. The first TextBlock is the rich label;
	# Generic.xaml's final TextBlock is only the button-type glyph.
	label = RawElement("TextBlock", "TextBlock", text="\ue9b7 Open website")
	type_glyph = RawElement("TextBlock", text="\ue9b7")
	button = RawElement("ReplyMarkupInlineButton", children=[label, type_glyph])
	monkeypatch.setitem(
		sys.modules,
		"UIAHandler",
		SimpleNamespace(
			handler=SimpleNamespace(
				baseTreeWalker=RawWalker(),
				baseCacheRequest="baseCache",
			),
			UIA=SimpleNamespace(
				UIA_ClassNamePropertyId="class",
				UIA_AutomationIdPropertyId="automationId",
				UIA_NamePropertyId="name",
			),
			UIA_TextPatternId="textPattern",
			IUIAutomationTextPattern="textPatternInterface",
		),
	)
	button_obj = SimpleNamespace(UIAElement=button)
	namespace["log"] = SimpleNamespace(debug=lambda *args, **kwargs: None)

	assert namespace["_inline_button_descendant_text"](button_obj) == "Open website"
	assert namespace["_inline_button_descendant_text"](button_obj) == "Open website"
	assert requested_lengths == [512]
	assert namespace["_clean_inline_button_text"]("\ue9b7 Open website") == "Open website"
	helper_source = ast.get_source_segment(
		SOURCE_PATH.read_text(encoding="utf-8"),
		next(
			node
			for node in ast.parse(SOURCE_PATH.read_text(encoding="utf-8")).body
			if isinstance(node, ast.FunctionDef) and node.name == "_inline_button_descendant_text"
		),
	)
	assert ".findFirst(" not in helper_source
	assert ".findAll(" not in helper_source
	assert "GetNextSiblingElementBuildCache" not in helper_source
	assert "GetFirstChildElementBuildCache" in helper_source
	assert "GetLastChildElementBuildCache" not in helper_source
	assert "GetCachedPattern" in helper_source
	assert "GetText(-1)" not in helper_source


def test_inline_button_text_pattern_read_is_queued_off_the_main_thread(monkeypatch):
	jobs = []
	main_queue_calls = []
	monkeypatch.setitem(
		sys.modules,
		"UIAHandler",
		SimpleNamespace(
			handler=SimpleNamespace(
				MTAThreadQueue=SimpleNamespace(put_nowait=jobs.append),
			),
		),
	)
	namespace = _load_module_members(
		{"_queue_inline_button_text_read"},
		{
			"_inline_button_descendant_text": lambda obj: "Open website",
			"queueHandler": SimpleNamespace(
				eventQueue="eventQueue",
				queueFunction=lambda queue, callback, *args: main_queue_calls.append(
					(queue, callback, args)
				),
			),
			"log": SimpleNamespace(debug=lambda *args, **kwargs: None),
		},
	)
	received = []

	assert namespace["_queue_inline_button_text_read"](object(), received.append)
	assert len(jobs) == 1
	assert not main_queue_calls
	assert not received

	jobs[0]()
	assert len(main_queue_calls) == 1
	queue, callback, args = main_queue_calls[0]
	assert queue == "eventQueue"
	callback(*args)
	assert received == ["Open website"]

	# A superseded focus must be discarded before it performs the slow UIA read.
	jobs.clear()
	main_queue_calls.clear()
	assert namespace["_queue_inline_button_text_read"](
		object(),
		received.append,
		is_current=lambda: False,
	)
	jobs[0]()
	assert not main_queue_calls


def test_inline_button_workaround_is_narrow_and_marked_for_removal():
	role = SimpleNamespace(LISTITEM="listItem", LIST="list")
	parent = Node(role=role.LIST, class_name="ReplyMarkupInlinePanel")
	button = Node(role=role.LISTITEM, parent=parent, class_name="Button")
	recovered = []
	namespace = _load_module_members(
		{
			"_is_inline_button_list_item",
			"_find_ancestor_by_automation_id",
			"ReplyMarkupInlineButtonListItem",
		},
		{
			"Role": role,
			"_inline_button_descendant_text": lambda obj: recovered.append(obj) or "Open website",
		},
	)
	source = SOURCE_PATH.read_text(encoding="utf-8")

	assert namespace["_is_inline_button_list_item"](button)
	message = Node(automation_id="Message_item")
	parent.UIAClassName = "List"
	parent.UIAAutomationId = "Markup"
	parent.parent = message
	assert namespace["_is_inline_button_list_item"](button)
	# Unigram 12.9's raw UIA view can insert a layout wrapper as the direct parent.
	parent.role = "group"
	assert namespace["_is_inline_button_list_item"](button)
	parent.UIAClassName = "List"
	parent.UIAAutomationId = "ChatsList"
	parent.parent = None
	assert not namespace["_is_inline_button_list_item"](button)
	assert "ReplyMarkupInlineButtonListItem" in source
	assert "AccessibilityView.Raw" in source
	assert "TODO: Remove" in source
	overlay_source = ast.get_source_segment(
		source,
		next(
			node
			for node in ast.parse(source).body
			if isinstance(node, ast.ClassDef) and node.name == "ReplyMarkupInlineButtonListItem"
		),
	)
	assert "_inline_button_descendant_text" in overlay_source
	assert "_unigramPlusInlineButtonName" in overlay_source
	assert "super().name" not in overlay_source

	class SlowProviderName:
		@property
		def name(self):
			raise AssertionError("Unigram's current UIA Name property must not be requested")

	class InlineButton(namespace["ReplyMarkupInlineButtonListItem"], SlowProviderName):
		pass

	inline_button = InlineButton()
	assert inline_button._get_name() == "Open website"
	assert recovered == [inline_button]
	inline_button._unigramPlusInlineButtonName = "Cached label"
	assert inline_button._get_name() == "Cached label"
	assert recovered == [inline_button]


def test_saved_messages_topic_type_name_is_replaced_with_visible_title(monkeypatch):
	class RawTitle:
		def GetCurrentPropertyValueEx(self, property_id, ignore_default):
			assert property_id == "name"
			assert ignore_default is True
			return "Project chat"

	client = SimpleNamespace(
		CreatePropertyCondition=lambda property_id, value: (property_id, value),
	)
	monkeypatch.setitem(
		sys.modules,
		"UIAHandler",
		SimpleNamespace(
			handler=SimpleNamespace(clientObject=client),
			TreeScope_Descendants="descendants",
			UIA=SimpleNamespace(
				UIA_AutomationIdPropertyId="automationId",
				UIA_NamePropertyId="name",
			),
		),
	)
	chat = Node("Telegram.Td.Api.SavedMessagesTopic")
	chat.UIAElement = SimpleNamespace(findFirst=lambda scope, condition: RawTitle())
	namespace = _load_module_members(
		{"_repair_saved_messages_topic_name"},
		{"_SAVED_MESSAGES_TOPIC_TYPE_NAME": "Telegram.Td.Api.SavedMessagesTopic"},
	)

	assert namespace["_repair_saved_messages_topic_name"](chat) == "Project chat"
	assert "ChatCell.GetAutomationName handles" in SOURCE_PATH.read_text(encoding="utf-8")


def test_shift_delete_remains_bound_but_alt_end_is_removed():
	source = SOURCE_PATH.read_text(encoding="utf-8")

	assert 'gesture="kb:shift+delete"' in source
	assert 'gesture="kb:ALT+end"' not in source
	assert "def script_to_down" not in source


def test_alt_c_classic_view_is_the_persisted_default():
	config = (ROOT / "addon" / "appModules" / "cnf.py").read_text(encoding="utf-8")
	settings = (ROOT / "addon" / "GlobalPlugins" / "UnigramPlus" / "__init__.py").read_text(
		encoding="utf-8-sig"
	)

	assert '"displayMessagesInWebView = boolean(default=False)"' in config
	assert '_("Display message text in a web view when pressing Alt+C")' in settings
	assert 'conf.set("displayMessagesInWebView", self.displayMessagesInWebView.IsChecked())' in settings
