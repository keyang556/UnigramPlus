"""Helpers for identifying and reading Unigram rich-message UIA trees.

Unigram renders ``MessageRichMessage`` with an ``InstantContent`` control.  The
control contains a ``LayoutRoot`` whose direct children correspond to the rich
message's page blocks.  Keeping this module independent from NVDA makes the UIA
tree handling straightforward to regression test.
"""

from collections import deque


_RICH_MESSAGE_CLASS = "instantcontent"
_LAYOUT_ROOT_AUTOMATION_ID = "LayoutRoot"
_DEFAULT_MAX_DEPTH = 12
_DEFAULT_MAX_NODES = 1000


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
