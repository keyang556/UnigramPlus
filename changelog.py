# A fake funct so that Gettext can search this file.
def _(t): return t

value = _(
	"- Fixed Alt+C failing when WhatsApp Enhancer is installed due to an appModules helper module name collision.\n"
	"- Changed the shortcut for announcing the installed Unigram and UnigramPlus versions from NVDA+Shift+V to NVDA+Alt+V to avoid shortcut conflicts.\n"
	"- Fixed Shift+Delete for deleting chats and leaving groups or channels in current Unigram versions, including automatic popup confirmation handling."
)
