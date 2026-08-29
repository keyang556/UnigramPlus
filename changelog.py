# A fake funct so that Gettext can search this file.
def _(t): return t

value = _(
	"- UnigramPlus is now tested with NVDA 2026.2 and uses NVDA's modern dialog APIs, with fallbacks for older NVDA versions.\n"
	"- Removed the temporary Saved Messages topic name fix after Unigram 12.10.1 added proper accessible names for Saved Messages chat rows.\n"
	"- Updated all translations and manuals for version 5.6.9."
)
