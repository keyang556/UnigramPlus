# A fake funct so that Gettext can search this file.
def _(t): return t

value = _(
	"- Fixed file-transfer progress tracking so it stops at 100% and no longer creates a new thread on every polling cycle.\n"
	"- When Unigram opens, focus now moves automatically to the chat list.\n"
	"- Added Ctrl+Alt+Up/Down to move through chats with unread mentions."
)
