"""Browse-mode presentation for Unigram messages with delegated UIA links."""

from html import escape
import os
import re


_INTERNAL_LINK_PATTERN = re.compile(
	r'<a href="nvda-action://unigram-link-\d+">(?P<label>.*?)</a>',
	re.DOTALL,
)


def _without_internal_links(message_html):
	"""Remove unsupported internal hrefs while preserving their escaped labels."""
	return _INTERNAL_LINK_PATTERN.sub(r"\g<label>", message_html)


def _activate_uia_link(link):
	try:
		link.doAction()
	except Exception:
		from logHandler import log

		log.exception("Could not activate a Unigram link from the rich-message dialog")


def _delegate_link(dialog, link, wx):
	# Close first so the action is performed with Unigram restored as the active
	# window. CallAfter also lets the WebView finish handling its navigation event.
	dialog.Close()
	wx.CallAfter(_activate_uia_link, link)


def show_browseable_message(message_html, title, link_actions=None):
	"""Show safe generated HTML and bridge internal links back to Unigram.

	``message_html`` must come from ``extract_message_html_and_actions``, which
	escapes all UIA-provided text and URL attributes before they reach this
	dialog. On NVDA releases without action-aware HTML dialogs, internal links
	are rendered as plain text instead of navigating to an invalid URL.
	"""
	from ui import browseableMessage

	link_actions = link_actions or {}
	if not link_actions:
		browseableMessage(message_html, title, isHtml=True)
		return

	try:
		import globalVars
		import gui
		from gui.message import HtmlMessageDialog
		from utils.security import isRunningOnSecureDesktop
		import wx

		if not hasattr(HtmlMessageDialog, "registerAction"):
			raise ImportError("HtmlMessageDialog does not support actions")
	except (ImportError, AttributeError):
		browseableMessage(_without_internal_links(message_html), title, isHtml=True)
		return

	if isRunningOnSecureDesktop():
		# Let NVDA issue its standard secure-screen warning.
		browseableMessage(_without_internal_links(message_html), title, isHtml=True)
		return

	html_path = os.path.join(globalVars.appDir, "message.html")
	try:
		with open(html_path, encoding="utf-8") as template_file:
			document = (
				template_file.read().replace("{{TITLE}}", escape(title)).replace("{{MESSAGE}}", message_html)
			)
		dialog = HtmlMessageDialog(None, document, title, buttons=None)
		for action_name, link in link_actions.items():
			dialog.registerAction(
				action_name,
				lambda link=link: _delegate_link(dialog, link, wx),
			)
	except Exception:
		from logHandler import log

		log.exception("Could not create the action-aware rich-message dialog")
		browseableMessage(_without_internal_links(message_html), title, isHtml=True)
		return

	gui.mainFrame.prePopup()
	try:
		dialog.Show()
	finally:
		gui.mainFrame.postPopup()
