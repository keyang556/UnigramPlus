"""Helpers for identifying and reading Unigram rich-message UIA trees.

Unigram renders ``MessageRichMessage`` with an ``InstantContent`` control.  The
control contains a ``LayoutRoot`` whose direct children correspond to the rich
message's page blocks.  Keeping this module independent from NVDA makes the UIA
tree handling straightforward to regression test.
"""

from collections import deque
from html import escape
import unicodedata


_RICH_MESSAGE_CLASS = "instantcontent"
_NON_RICH_PRIMARY_CONTENT_CLASSES = (
	# Keep this list aligned with MessageBubble.UpdateMessageContentControl in
	# Unigram. InstantContent is reserved exclusively for MessageRichMessage;
	# every other non-text message type uses one of these controls.
	"WebPageContent",
	"AlbumContent",
	"PaidMediaContent",
	"AnimationContent",
	"AudioContent",
	"CallContent",
	"ContactContent",
	"DiceContent",
	"DocumentContent",
	"GameContent",
	"PhotoContent",
	"InvoicePreviewContent",
	"InvoicePhotoContent",
	"InvoiceContent",
	"LiveLocationContent",
	"LocationContent",
	"PollContent",
	"ChecklistContent",
	"StickerContent",
	"StakeDiceContent",
	"VenueContent",
	"VideoContent",
	"VideoNoteContent",
	"VoiceNoteContent",
	"GiveawayContent",
	"AspectView",
	"SponsoredContent",
	"UnsupportedContent",
)
_NON_RICH_PRIMARY_CONTENT_CLASS_KEYS = frozenset(
	class_name.casefold() for class_name in _NON_RICH_PRIMARY_CONTENT_CLASSES
)
_LAYOUT_ROOT_AUTOMATION_ID = "LayoutRoot"
_DEFAULT_MAX_DEPTH = 12
_DEFAULT_MAX_NODES = 1000
_MESSAGE_TEXT_AUTOMATION_IDS = frozenset(("TextBlock", "Message", "Question", "QuestionText", "RecognizedText"))


def _safe_attr(obj, name, default=""):
	try:
		return getattr(obj, name, default)
	except Exception:
		return default


def _children(obj):
	children = _safe_attr(obj, "children", ())
	try:
		return tuple(children or ())
	except Exception:
		return ()


def _class_name(obj):
	class_name = str(_safe_attr(obj, "UIAClassName", "") or "")
	return class_name.replace(":", ".").rsplit(".", 1)[-1].casefold()


def _is_instant_content(obj):
	return _class_name(obj) == _RICH_MESSAGE_CLASS


def _message_text_nodes(message):
	return tuple(
		node
		for node in _children(message)
		if _safe_attr(node, "UIAAutomationId", "") in _MESSAGE_TEXT_AUTOMATION_IDS
	)


def _has_meaningful_message_text(message):
	"""Whether a direct text control contains more than the rich empty comma."""
	for node in _message_text_nodes(message):
		text = _clean_text(_safe_attr(node, "name", ""))
		if text.strip(" ,，"):
			return True
	return False


def _node_identity(node):
	"""Return a stable identity for NVDA objects and raw-UIA wrappers."""
	element = _safe_attr(node, "_element", None)
	return id(element) if element is not None else id(node)


def _find_only_rich_content(message, max_depth=_DEFAULT_MAX_DEPTH, max_nodes=_DEFAULT_MAX_NODES):
	"""Find InstantContent only when it is the message's sole primary content.

	Unigram recycles message bubbles. A stale ``InstantContent`` subtree may
	therefore coexist briefly with the current sticker, animated emoji, media, or
	text control. The C# ``UpdateMessageContentControl`` switch makes the active
	controls mutually exclusive, so any such sibling proves this is not a
	``MessageRichMessage``. Empty Message/TextBlock nodes are deliberately ignored:
	they are present in the Sophie-style rich-message UIA tree reported by NVDA.
	"""
	queue = deque((child, 1) for child in _children(message))
	seen = {_node_identity(message)}
	visited = 0
	rich_root = None
	while queue and visited < max_nodes:
		node, depth = queue.popleft()
		identity = _node_identity(node)
		if identity in seen:
			continue
		seen.add(identity)
		visited += 1
		if bool(_safe_attr(node, "isOffscreen", False)):
			continue
		if _is_instant_content(node):
			# Two visible InstantContent trees are ambiguous and most likely a
			# recycled template in transition. Do not announce either one.
			if rich_root is not None:
				return None
			rich_root = node
			# Rich page blocks may use controls whose class names overlap with
			# ordinary media. They belong to this root, so do not classify them.
			continue
		if _class_name(node) in _NON_RICH_PRIMARY_CONTENT_CLASS_KEYS:
			return None
		if (
			_safe_attr(node, "UIAAutomationId", "") in _MESSAGE_TEXT_AUTOMATION_IDS
			and _clean_text(_safe_attr(node, "name", ""))
		):
			return None
		if depth < max_depth:
			queue.extend((child, depth + 1) for child in _children(node))
	return rich_root


class _RawUIANode:
	"""Expose a raw UIA element through the small interface used by this module."""

	def __init__(self, element, walker, uia, text_pattern_id=None, text_pattern_interface=None):
		self._element = element
		self._walker = walker
		self._uia = uia
		self._text_pattern_id = text_pattern_id
		self._text_pattern_interface = text_pattern_interface

	def _property(self, property_id):
		try:
			return self._element.GetCurrentPropertyValueEx(property_id, True) or ""
		except Exception:
			return ""

	@property
	def name(self):
		name = self._property(self._uia.UIA_NamePropertyId)
		if name:
			return name
		if self._text_pattern_id is None or self._text_pattern_interface is None:
			return ""
		try:
			pattern = self._element.GetCurrentPattern(self._text_pattern_id)
			pattern = pattern.QueryInterface(self._text_pattern_interface)
			return pattern.DocumentRange.GetText(-1) or ""
		except Exception:
			return ""

	@property
	def UIAClassName(self):
		return self._property(self._uia.UIA_ClassNamePropertyId)

	@property
	def UIAAutomationId(self):
		return self._property(self._uia.UIA_AutomationIdPropertyId)

	@property
	def isOffscreen(self):
		return bool(self._property(self._uia.UIA_IsOffscreenPropertyId))

	@property
	def children(self):
		children = []
		try:
			element = self._walker.GetFirstChildElement(self._element)
			while element is not None and len(children) < _DEFAULT_MAX_NODES:
				children.append(
					_RawUIANode(
						element,
						self._walker,
						self._uia,
						self._text_pattern_id,
						self._text_pattern_interface,
					)
				)
				element = self._walker.GetNextSiblingElement(element)
		except Exception:
			pass
		return children


def _find_raw_rich_message_root(message):
	"""Search the raw UIA view, where non-control containers are still visible.

	Returns ``(available, result)``. ``FindFirst`` is used because InstantContent
	can be deeper than NVDA's exposed control view. Only competing controls under
	the same ``Media`` parent are relevant; matching controls in a reply preview or
	inside the rich page must not suppress the real rich message.
	"""
	element = _safe_attr(message, "UIAElement", None)
	if element is None:
		return False, None
	try:
		import UIAHandler

		handler = UIAHandler.handler
		client = handler.clientObject
		visible_condition = client.CreatePropertyCondition(
			UIAHandler.UIA.UIA_IsOffscreenPropertyId,
			False,
		)
		class_condition = client.CreatePropertyCondition(
			UIAHandler.UIA.UIA_ClassNamePropertyId,
			"InstantContent",
		)
		condition = client.createAndConditionFromArray([class_condition, visible_condition])
		result = element.findFirst(UIAHandler.TreeScope_Descendants, condition)
		if result is None:
			return True, None

		# MessageBubble.xaml hosts the mutually exclusive content control inside
		# the Media border. A sticker/media sibling means InstantContent is stale.
		walker = client.RawViewWalker
		parent = walker.GetParentElement(result)
		if parent is not None:
			sibling = walker.GetFirstChildElement(parent)
			while sibling is not None:
				node = _RawUIANode(sibling, walker, UIAHandler.UIA)
				if not node.isOffscreen:
					class_name = _class_name(node)
					if class_name in _NON_RICH_PRIMARY_CONTENT_CLASS_KEYS:
						return True, None
					if class_name == _RICH_MESSAGE_CLASS and sibling is not result:
						try:
							if not client.CompareElements(sibling, result):
								return True, None
						except Exception:
							return True, None
				sibling = walker.GetNextSiblingElement(sibling)

		return True, _RawUIANode(
			result,
			client.RawViewWalker,
			UIAHandler.UIA,
			UIAHandler.UIA_TextPatternId,
			UIAHandler.IUIAutomationTextPattern,
		)
	except Exception:
		return False, None


def _walk_descendants(root, max_depth=_DEFAULT_MAX_DEPTH, max_nodes=_DEFAULT_MAX_NODES):
	"""Yield a bounded breadth-first walk, tolerating stale and cyclic UIA nodes."""
	queue = deque((child, 1) for child in _children(root))
	seen = {_node_identity(root)}
	visited = 0
	while queue and visited < max_nodes:
		node, depth = queue.popleft()
		identity = _node_identity(node)
		if identity in seen:
			continue
		seen.add(identity)
		visited += 1
		yield node
		if depth < max_depth:
			queue.extend((child, depth + 1) for child in _children(node))


def _rich_content_matches_message(message, root):
	"""Whether readable rich text, when present, belongs to this message."""
	rich_text = _clean_text(extract_rich_message_text(root))
	if not rich_text:
		# Some MessageRichMessage page blocks have no UIA text. Unigram then
		# contributes only `", "` to the accessible summary, producing the
		# Sophie-style comma/blank content described in the NVDA log.
		return has_empty_rich_message_summary(message)

	# MessageRichMessage is summarized by Unigram with RichMessage.ToPlainText.
	# Require the active message's accessible surface to corroborate the root so
	# a populated InstantContent left by a recycled message cannot be mistaken for
	# the new sticker, animated emoji, big emoji, or ordinary text message.
	surface = _text_for_surface_comparison(_safe_attr(message, "name", ""))
	return not surface or _text_for_surface_comparison(rich_text) in surface


def has_empty_rich_message_summary(message):
	"""Recognize Unigram's empty MessageRichMessage summary.

	``Automation.GetSummary`` returns ``ToPlainText() + ", "`` for a rich
	message. In the Sophie-style group layout the first line is the sender and the
	second line starts with that otherwise empty content comma. In a direct chat,
	the single line starts with the same comma and contains no second comma before
	the status. Ordinary comma-prefixed text has another comma separating its real
	content from the status. These signatures do not depend on localized strings
	or provider-generated child names.
	"""
	lines = [line.strip() for line in _clean_text(_safe_attr(message, "name", "")).split("\n")]
	if len(lines) > 1:
		return lines[1].startswith(",")
	return bool(lines[0]) and lines[0].startswith(",") and lines[0].count(",") == 1


def is_rich_message(message):
	"""Whether a message has either the official rich summary or rich UIA root.

	Empty rich pages do not consistently expose ``InstantContent`` through NVDA,
	but their accessible name remains unambiguous: Unigram's
	``Automation.GetSummary`` emits ``ToPlainText() + ", "``. Some UIA provider
	versions also expose that comma as the Message control's name, so the official
	summary signature must take precedence over the normal text-control guard.
	"""
	if message is None:
		return False
	if has_empty_rich_message_summary(message):
		# This visible summary is the authoritative MessageRichMessage signature
		# in current Unigram. Provider-generated child text must not override it.
		return True
	has_meaningful_text = _has_meaningful_message_text(message)
	if has_meaningful_text:
		return False
	return find_rich_message_root(message) is not None


def find_rich_message_root(message):
	"""Return the ``InstantContent`` descendant of a message, if present."""
	if message is None:
		return None
	if _is_instant_content(message):
		return message
	# UpdateMessageText explicitly excludes MessageRichMessage. Any populated
	# direct text control therefore belongs to another message type.
	if _has_meaningful_message_text(message):
		return None
	raw_available, raw_root = _find_raw_rich_message_root(message)
	if raw_available:
		if raw_root is None:
			return None
		if _rich_content_matches_message(message, raw_root):
			return raw_root
		return None
	root = _find_only_rich_content(message)
	if root is None:
		return None
	if _rich_content_matches_message(message, root):
		return root
	return None


def insert_hint_before_status(name, hint, status_markers):
	"""Insert a rich-message hint immediately before the trailing send/receive status."""
	name = _clean_text(name)
	hint = _clean_text(hint)
	if not hint or hint in name:
		return name
	positions = [name.rfind(marker) for marker in status_markers if marker]
	positions = [position for position in positions if position >= 0]
	if not positions:
		return "%s. %s" % (name.rstrip(". "), hint) if name else hint
	position = max(positions)
	prefix = name[:position].rstrip(". ")
	suffix = name[position:]
	return "%s. %s%s" % (prefix, hint, suffix) if prefix else "%s%s" % (hint, suffix)


def extract_message_text(message):
	"""Collect all text controls flattened into a message's control-view children."""
	parts = []
	for node in _message_text_nodes(message):
		text = _clean_text(_safe_attr(node, "name", ""))
		if text and text not in parts:
			parts.append(text)
	return "\n\n".join(parts)


def merge_message_html_and_rich_text(message_html, message_text, rich_text):
	"""Append distinct rich text to already generated message HTML safely."""
	rich_text = _clean_text(rich_text)
	if not rich_text:
		return message_html
	message_text = _clean_text(message_text)
	if message_text and _text_for_comparison(rich_text) in _text_for_comparison(message_text):
		return message_html
	blocks = []
	for block in rich_text.split("\n\n"):
		block = _clean_text(block)
		if block:
			blocks.append("<p>%s</p>" % escape(block).replace("\n", "<br>"))
	return message_html + "".join(blocks)


def _is_link(node):
	role = _safe_attr(node, "role", None)
	role_name = _safe_attr(role, "name", "")
	return str(role_name).casefold() == "link"


def _link_url(node):
	label = _clean_text(_safe_attr(node, "name", ""))
	if label.startswith(("https://", "http://", "tg://", "mailto:")):
		return label
	if label.startswith("www."):
		return "https://" + label
	for attribute in ("value", "description", "helpText", "UIAHelpText"):
		value = _clean_text(_safe_attr(node, attribute, ""))
		if value.startswith(("https://", "http://", "tg://", "mailto:")):
			return value
	try:
		import UIAHandler

		element = _safe_attr(node, "UIAElement", None)
		if element is not None:
			value = element.GetCurrentPropertyValueEx(
				UIAHandler.UIA.UIA_HelpTextPropertyId,
				True,
			)
			value = _clean_text(value)
			if value.startswith(("https://", "http://", "tg://", "mailto:")):
				return value
	except Exception:
		pass
	return None


def _text_with_links_to_html(text, links):
	parts = []
	actions = {}
	unmatched = []
	position = 0
	for label, url, action in links:
		index = text.find(label, position)
		if index < 0:
			unmatched.append((label, url, action))
			continue
		parts.append(escape(text[position:index]))
		parts.append(_link_to_html(label, url, action))
		if action:
			actions[action[0]] = action[1]
		position = index + len(label)
	parts.append(escape(text[position:]))
	for label, url, action in unmatched:
		parts.append("<br>%s" % _link_to_html(label, url, action))
		if action:
			actions[action[0]] = action[1]
	return "".join(parts).replace("\n", "<br>"), actions


def _link_to_html(label, url, action):
	href = escape(url, quote=True)
	if action:
		# MSHTML's accessibility action does not reliably navigate unknown URL
		# schemes. Explicitly assigning location from the click event ensures both
		# Enter and Space reach HtmlMessageDialog._onNavigating.
		return (
			'<a href="%s" onclick="window.location.href=this.href; return false;">%s</a>'
			% (href, escape(label))
		)
	return '<a href="%s">%s</a>' % (href, escape(label))


def extract_message_html_and_actions(message):
	"""Build safe HTML and UIA actions for links whose URL is not exposed.

	Unigram's UIA provider exposes some links as actionable controls without a
	URL property.  Those links use NVDA's internal action URL and retain the
	original UIA object so the browse-mode dialog can delegate activation back
	to Unigram.
	"""
	blocks = []
	actions = {}
	next_action = 0
	for node in _message_text_nodes(message):
		text = _clean_text(_safe_attr(node, "name", ""))
		if not text:
			continue
		links = []
		for descendant in _walk_descendants(node, max_depth=6, max_nodes=200):
			if not _is_link(descendant):
				continue
			label = _clean_text(_safe_attr(descendant, "name", ""))
			if not label:
				continue
			url = _link_url(descendant)
			if url and url.startswith(("https://", "http://")):
				links.append((label, url, None))
			else:
				action_name = "unigram-link-%d" % next_action
				next_action += 1
				links.append(
					(
						label,
						"nvda-action://%s" % action_name,
						(action_name, descendant),
					)
				)
		content, block_actions = _text_with_links_to_html(text, links)
		actions.update(block_actions)
		blocks.append("<p>%s</p>" % content)
	return "".join(blocks), actions


def extract_message_html(message):
	"""Build safe semantic HTML from flattened text blocks and their UIA links."""
	return extract_message_html_and_actions(message)[0]


def _clean_text(value):
	try:
		text = str(value or "")
	except Exception:
		return ""
	return "\n".join(line.rstrip() for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")).strip()


def _text_for_comparison(value):
	"""Normalize case and whitespace when checking whether content is duplicated."""
	return " ".join(_clean_text(value).casefold().split())


def _text_for_surface_comparison(value):
	"""Also collapse punctuation inserted by Unigram's accessible summary."""
	text = _clean_text(value).casefold()
	return " ".join(
		"".join(
			" " if char.isspace() or unicodedata.category(char).startswith(("P", "Z")) else char
			for char in text
		).split()
	)


def _text_for_block(block):
	"""Get one block's accessible text without repeating descendant names."""
	name = _clean_text(_safe_attr(block, "name", ""))
	if name:
		return name

	parts = []
	for node in _walk_descendants(block):
		text = _clean_text(_safe_attr(node, "name", ""))
		if text and text not in parts:
			parts.append(text)
	return "\n".join(parts)


def extract_rich_message_text(root, text_info_position=None):
	"""Extract readable block-separated text from an ``InstantContent`` control."""
	if root is None:
		return ""

	layout = next(
		(
			node
			for node in _walk_descendants(root)
			if _safe_attr(node, "UIAAutomationId", "") == _LAYOUT_ROOT_AUTOMATION_ID
		),
		None,
	)
	container = layout or root
	blocks = []
	for child in _children(container):
		text = _text_for_block(child)
		if text and (not blocks or text != blocks[-1]):
			blocks.append(text)
	if blocks:
		return "\n\n".join(blocks)

	# Some UIA providers flatten the LayoutRoot children.  TextInfo is a useful
	# fallback on those versions, but is optional so this helper remains testable
	# without importing NVDA.
	if text_info_position is not None:
		try:
			return _clean_text(root.makeTextInfo(text_info_position).text)
		except Exception:
			pass
	return _clean_text(_safe_attr(root, "name", ""))
