import ast
from pathlib import Path
import sys
from types import SimpleNamespace
import warnings


sys.path.insert(0, str(Path(__file__).parents[1] / "addon" / "appModules"))

from rich_message import (  # noqa: E402
	extract_message_text,
	extract_rich_message_text,
	find_rich_message_root,
	insert_hint_before_status,
)


class Node:
	def __init__(self, *, name="", class_name="", automation_id="", children=None):
		self.name = name
		self.UIAClassName = class_name
		self.UIAAutomationId = automation_id
		self.children = children or []


def test_finds_namespaced_instant_content_below_message():
	rich = Node(class_name="Telegram.Controls.Messages.Content.InstantContent")
	message = Node(children=[Node(children=[rich])])

	assert find_rich_message_root(message) is rich


def test_does_not_misclassify_an_unrelated_layout_root():
	message = Node(children=[Node(automation_id="LayoutRoot", children=[Node(name="ordinary message")])])

	assert find_rich_message_root(message) is None


def test_finds_and_extracts_instant_content_from_raw_uia_view(monkeypatch):
	class UiaConstants:
		UIA_NamePropertyId = 1
		UIA_ClassNamePropertyId = 2
		UIA_AutomationIdPropertyId = 3
		UIA_IsOffscreenPropertyId = 5

	class Element:
		def __init__(
			self,
			*,
			name="",
			class_name="",
			automation_id="",
			text_pattern_text=None,
			children=None,
		):
			self.properties = {1: name, 2: class_name, 3: automation_id}
			self.text_pattern_text = text_pattern_text
			self.children = children or []

		def GetCurrentPropertyValueEx(self, property_id, ignore_default):
			return self.properties.get(property_id, "")

		def findFirst(self, scope, condition):
			assert scope == "descendants"
			self.find_condition = condition
			return self.find_result

		def GetCurrentPattern(self, pattern_id):
			assert pattern_id == 4
			if self.text_pattern_text is None:
				raise RuntimeError("TextPattern unavailable")
			return Pattern(self.text_pattern_text)

	class Pattern:
		def __init__(self, text):
			self.DocumentRange = SimpleNamespace(GetText=lambda max_length: text)

		def QueryInterface(self, interface):
			assert interface == "IUIAutomationTextPattern"
			return self

	class Walker:
		def GetFirstChildElement(self, element):
			return element.children[0] if element.children else None

		def GetNextSiblingElement(self, element):
			return siblings.get(id(element))

	first_text = Element(text_pattern_text="First raw block")
	second_text = Element(text_pattern_text="Second raw block")
	layout = Element(automation_id="LayoutRoot", children=[first_text, second_text])
	rich = Element(class_name="InstantContent", children=[layout])
	siblings = {id(first_text): second_text}
	client = SimpleNamespace(
		RawViewWalker=Walker(),
		CreatePropertyCondition=lambda property_id, value: (property_id, value),
		createAndConditionFromArray=lambda conditions: tuple(conditions),
	)
	fake_uia_handler = SimpleNamespace(
		handler=SimpleNamespace(clientObject=client),
		UIA=UiaConstants,
		UIA_TextPatternId=4,
		IUIAutomationTextPattern="IUIAutomationTextPattern",
		TreeScope_Descendants="descendants",
	)
	monkeypatch.setitem(sys.modules, "UIAHandler", fake_uia_handler)
	message_element = Element()
	message_element.find_result = rich
	message = SimpleNamespace(UIAElement=message_element)

	root = find_rich_message_root(message)

	assert root.UIAClassName == "InstantContent"
	assert extract_rich_message_text(root) == "First raw block\n\nSecond raw block"
	assert (5, False) in message_element.find_condition


def test_collects_all_flattened_message_text_controls():
	message = Node(
		children=[
			Node(name="First paragraph", automation_id="TextBlock"),
			Node(name="Second paragraph", automation_id="TextBlock"),
			Node(name="recognized", automation_id="RecognizedText"),
			Node(name="18:17", automation_id="Footer"),
		]
	)

	assert extract_message_text(message) == "First paragraph\n\nSecond paragraph\n\nrecognized"


def test_extracts_layout_children_as_separate_markdown_blocks():
	layout = Node(
		automation_id="LayoutRoot",
		children=[
			Node(name="Heading"),
			Node(children=[Node(name="First paragraph"), Node(name="linked text")]),
			Node(name="Second paragraph\r\ncontinues"),
		],
	)
	rich = Node(class_name="InstantContent", children=[layout])

	assert extract_rich_message_text(rich) == (
		"Heading\n\nFirst paragraph\nlinked text\n\nSecond paragraph\ncontinues"
	)


def test_prefers_a_block_name_over_duplicate_descendant_names():
	block = Node(name="A sentence with a link", children=[Node(name="a link")])
	rich = Node(class_name="InstantContent", children=[Node(automation_id="LayoutRoot", children=[block])])

	assert extract_rich_message_text(rich) == "A sentence with a link"


def test_cyclic_uia_tree_is_bounded_and_safe():
	first = Node()
	second = Node()
	first.children = [second]
	second.children = [first]

	assert find_rich_message_root(first) is None
	assert extract_rich_message_text(first) == ""


def test_text_info_fallback_handles_flattened_provider():
	class TextInfo:
		text = "Fallback rich text"

	class FlatRichNode(Node):
		def makeTextInfo(self, position):
			assert position == "all"
			return TextInfo()

	rich = FlatRichNode(class_name="InstantContent")

	assert extract_rich_message_text(rich, "all") == "Fallback rich text"


def test_inserts_hint_before_localized_message_status():
	assert insert_hint_before_status(
		"Message content, Received at 18:17",
		"Rich message. Press Alt+C to browse",
		(", Sent at ", ", Received at "),
	) == "Message content. Rich message. Press Alt+C to browse, Received at 18:17"


def test_appends_hint_when_message_status_is_unavailable():
	assert insert_hint_before_status("Message content.", "Rich message", ()) == "Message content. Rich message"


def test_all_message_text_uses_browse_mode_when_rich_content_is_empty_or_absent():
	"""Exercise the actual Alt+C method body without importing NVDA."""
	source = (Path(__file__).parents[1] / "addon" / "appModules" / "unigram.py").read_text(encoding="utf-8")
	with warnings.catch_warnings():
		# unigram.py contains legacy replacement strings such as "\g<1>" outside
		# this method. Parsing the full module can warn about those unrelated lines.
		warnings.simplefilter("ignore", SyntaxWarning)
		module = ast.parse(source)
	message_class = next(node for node in module.body if isinstance(node, ast.ClassDef) and node.name == "Message_list_item")
	method = next(
		node
		for node in message_class.body
		if isinstance(node, ast.FunctionDef) and node.name == "script_show_text_message"
	)
	method.decorator_list = []

	message_item = SimpleNamespace(
		children=[
			SimpleNamespace(UIAAutomationId="TextBlock", name="Ordinary text"),
			SimpleNamespace(UIAAutomationId="RecognizedText", name="Recognized text"),
		]
	)
	for rich_root in (None, object()):
		opened = []
		namespace = {
			"find_rich_message_root": lambda obj, result=rich_root: result,
			"extract_rich_message_text": lambda root, position: "",
			"extract_message_text": extract_message_text,
			"textInfos": SimpleNamespace(POSITION_ALL="all"),
			"log": SimpleNamespace(debug=lambda text: None),
			"browseableMessage": lambda *args: opened.append(("browse", args)),
			"message": lambda text: opened.append(("message", text)),
			"_": lambda text: text,
		}
		exec(compile(ast.Module(body=[method], type_ignores=[]), "unigram.py", "exec"), namespace)

		namespace["script_show_text_message"](message_item, None)

		title = "Rich message" if rich_root else "message text"
		assert opened == [("browse", ("Ordinary text\n\nRecognized text", title))]


def test_focus_hint_uses_the_message_overlay_keywords():
	source = (Path(__file__).parents[1] / "addon" / "appModules" / "unigram.py").read_text(encoding="utf-8")
	with warnings.catch_warnings():
		warnings.simplefilter("ignore", SyntaxWarning)
		module = ast.parse(source)
	event_method = next(
		node
		for node in ast.walk(module)
		if isinstance(node, ast.FunctionDef) and node.name == "event_gainFocus"
	)
	rich_branch = next(
		node
		for node in ast.walk(event_method)
		if isinstance(node, ast.If)
		and isinstance(node.test, ast.Call)
		and isinstance(node.test.func, ast.Name)
		and node.test.func.id == "find_rich_message_root"
	)
	obj = SimpleNamespace(
		name="Content, Received at 18:17",
		keywords=("Seen", "Not seen", ", Sent at ", ", Received at "),
	)
	namespace = {
		"obj": obj,
		"find_rich_message_root": lambda candidate: object(),
		"insert_hint_before_status": insert_hint_before_status,
		"_": lambda text: text,
	}

	exec(compile(ast.Module(body=[rich_branch], type_ignores=[]), "unigram.py", "exec"), namespace)

	assert obj.name == "Content. Rich message. Press Alt+C to browse, Received at 18:17"
