# A fake funct so that Gettext can search this file.
def _(t): return t

value = _(
	"- Added NVDA+Shift+V to announce the installed Unigram and UnigramPlus versions.\n"
	"- Removed the temporary Unigram 12.9 inline-button workaround after Unigram 12.9.1 fixed button labels; this avoids UIA stalls in bot lists, message navigation, reactions, and the chat list.\n"
	"- Updated all translations and manuals for version 5.6.6."
)
