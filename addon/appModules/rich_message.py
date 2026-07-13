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
	return next((node for node in _walk_descendants(message) if _is_instant_content(node)), None)


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
