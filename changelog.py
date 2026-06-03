# A fake funct so that Gettext can search this file.
def _(t): return t

value = _(
"Fixed the identity button in a group or channel profile announcing \"Identity root\"; it now announces the chat name and member count. Fixed the typing sound stopping after a few seconds while the other side was still typing. Ctrl+C is no longer handled twice: it copies the link when the focus is on a link, and otherwise lets Unigram copy the message."
)
