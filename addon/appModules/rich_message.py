"""Helpers for identifying and reading Unigram rich-message UIA trees.

Unigram renders ``MessageRichMessage`` with an ``InstantContent`` control.  The
control contains a ``LayoutRoot`` whose direct children correspond to the rich
message's page blocks.  Keeping this module independent from NVDA makes the UIA
tree handling straightforward to regression test.
"""

from collections import deque
from html import escape


_RICH_MESSAGE_CLASS = "instantcontent"
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


def _is_instant_content(obj):
	class_name = str(_safe_attr(obj, "UIAClassName", "") or "")
	return class_name.replace(":", ".").rsplit(".", 1)[-1].casefold() == _RICH_MESSAGE_CLASS


def _message_text_nodes(message):
	return tuple(
		node
		for node in _children(message)
		if _safe_attr(node, "UIAAutomationId", "") in _MESSAGE_TEXT_AUTOMATION_IDS
	)


def _surface_has_message_text(message):
	"""Whether Unigram's unprocessed item summary already contains normal message text."""
	surface = _clean_text(_safe_attr(message, "name", "")).casefold()
	if not surface:
		return False
	for node in _message_text_nodes(message):
		text = _clean_text(_safe_attr(node, "name", "")).casefold()
		if text and text in surface:
			return True
	return False


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

	Returns ``(available, result)``. If raw UIA is available, callers should trust
	the native query even when no result was found instead of repeating an
	expensive Python walk of the same provider tree.
	"""
	element = _safe_attr(message, "UIAElement", None)
	if element is None:
		return False, None
	try:
		import UIAHandler

		handler = UIAHandler.handler
		client = handler.clientObject
		condition = client.CreatePropertyCondition(
			UIAHandler.UIA.UIA_ClassNamePropertyId,
			"InstantContent",
		)
		visible_condition = client.CreatePropertyCondition(
			UIAHandler.UIA.UIA_IsOffscreenPropertyId,
			False,
		)
		condition = client.createAndConditionFromArray([condition, visible_condition])
		result = element.findFirst(UIAHandler.TreeScope_Descendants, condition)
		if result is None:
			return True, None
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
	seen = {id(root)}
	visited = 0
	while queue and visited < max_nodes:
		node, depth = queue.popleft()
		identity = id(node)
		if identity in seen:
			continue
		seen.add(identity)
		visited += 1
		yield node
		if depth < max_depth:
			queue.extend((child, depth + 1) for child in _children(node))


def find_rich_message_root(message):
	"""Return the ``InstantContent`` descendant of a message, if present."""
	if message is None:
		return None
	if _is_instant_content(message):
		return message
	# A normal message exposes its TextBlock content in the list item's own UIA
	# summary. MessageRichMessage currently contributes only a separator comma;
	# its real PageBlock text lives below InstantContent. This guard also rejects
	# visible recycled InstantContent controls retained by ordinary message cells.
	if _surface_has_message_text(message):
		return None
	raw_available, raw_root = _find_raw_rich_message_root(message)
	if raw_available:
		return raw_root
	return next((node for node in _walk_descendants(message) if _is_instant_content(node)), None)


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
