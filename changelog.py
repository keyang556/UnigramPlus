# A fake funct so that Gettext can search this file.
def _(t): return t

value = _(
	"- Fixed an error that could occur when NVDA entered a secure desktop, such as a UAC prompt, while UnigramPlus background message tracking was enabled.\n"
	"- Restored reliable voice-message recording detection and avoided unnecessary end-of-chat UI Automation probes that could delay message navigation.\n"
	"- Removed the obsolete Saved Messages topic name workaround; current Unigram versions now provide accessible names for Saved Messages chats natively.\n"
	"- Updated compatibility for NVDA 2026.2.\n"
	"- Updated Polish and Burmese translations."
)
