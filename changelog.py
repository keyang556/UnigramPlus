# A fake funct so that Gettext can search this file.
def _(t): return t

value = _(
	"- Fixed Shift+Delete by using Unigram's native Delete command and automatically confirming deletion for both sides.\n"
	"- Alt+2 now uses Unigram's Go to bottom button first, and the duplicate Alt+End shortcut was removed.\n"
	"- Added a setting to choose between the classic window (default) and web view when displaying message text with Alt+C.\n"
	"- Unigram's official rich-message text is now used, with a temporary fix for unlabeled inline buttons in Unigram 12.9.\n"
	"- Updated every localized manual with the Unigram 12.9 shortcut list.\n"
	"- Added a temporary fix so Saved Messages topic rows announce the visible chat title instead of a TDLib type name."
)
