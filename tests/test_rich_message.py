import ast
from pathlib import Path
import sys
from types import SimpleNamespace
import warnings


sys.path.insert(0, str(Path(__file__).parents[1] / "addon" / "appModules"))

from rich_message import extract_rich_message_text, find_rich_message_root  # noqa: E402


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

	class Element:
		def __init__(self, *, name="", class_name="", automation_id="", children=None):
			self.properties = {1: name, 2: class_name, 3: automation_id}
			self.children = children or []

		def GetCurrentPropertyValueEx(self, property_id, ignore_default):
			return self.properties.get(property_id, "")

		def findFirst(self, scope, condition):
			assert scope == "descendants"
			return condition

	class Walker:
		def GetFirstChildElement(self, element):
			return element.children[0] if element.children else None

		def GetNextSiblingElement(self, element):
			return siblings.get(id(element))

	text = Element(name="Raw rich text")
	layout = Element(automation_id="LayoutRoot", children=[text])
	rich = Element(class_name="InstantContent", children=[layout])
	siblings = {}
	client = SimpleNamespace(
		RawViewWalker=Walker(),
		CreatePropertyCondition=lambda property_id, value: rich,
	)
	fake_uia_handler = SimpleNamespace(
		handler=SimpleNamespace(clientObject=client),
		UIA=UiaConstants,
		TreeScope_Descendants="descendants",
	)
	monkeypatch.setitem(sys.modules, "UIAHandler", fake_uia_handler)
	message = SimpleNamespace(UIAElement=Element())

	root = find_rich_message_root(message)

	assert root.UIAClassName == "InstantContent"
	assert extract_rich_message_text(root) == "Raw rich text"


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


def test_empty_rich_content_falls_back_to_ordinary_message_text():
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

	opened = []
	namespace = {
		"find_rich_message_root": lambda obj: object(),
		"extract_rich_message_text": lambda root, position: "",
		"textInfos": SimpleNamespace(POSITION_ALL="all"),
		"browseableMessage": lambda *args: opened.append(("browse", args)),
		"message": lambda text: opened.append(("message", text)),
		"TextWindow": lambda *args, **kwargs: opened.append(("window", args, kwargs)),
		"_": lambda text: text,
	}
	exec(compile(ast.Module(body=[method], type_ignores=[]), "unigram.py", "exec"), namespace)
	message_item = SimpleNamespace(
		children=[
			SimpleNamespace(UIAAutomationId="TextBlock", name="Ordinary text"),
			SimpleNamespace(UIAAutomationId="RecognizedText", name="Recognized text"),
		]
	)

	namespace["script_show_text_message"](message_item, None)

	assert opened == [
		("window", ("Ordinary text\n\nRecognized text", "message text"), {"readOnly": False})
	]
