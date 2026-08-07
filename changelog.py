# A fake funct so that Gettext can search this file.
def _(t): return t

value = _(
	"- Fixed an intermittent issue where NVDA announced \"list\" before a message while navigating with the Up and Down Arrow keys.\n"
	"- Added a setting for the Alt+[ behavior that announces message headers after their content; it is disabled by default.\n"
	"- Added an optional sound notification when reaching the end of a chat."
)
