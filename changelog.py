# A fake funct so that Gettext can search this file.
def _(t): return t

value = _(
	"""- Fixed NVDA errors with the Unigram WinUI 3 beta each time you switched back to Unigram or typed with an input method (IME).
- UnigramPlus no longer interferes with focus announcements in Telegram Desktop when the Telegram Desktop add-on is not installed.
- Removed the notification when a voice or video message recording is canceled: Unigram 13.0 and later announce it themselves, so it is no longer heard twice.
- Updated the Polish and Vietnamese translations."""
)
