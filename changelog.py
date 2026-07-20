# A fake funct so that Gettext can search this file.
def _(t): return t

value = _(
	"- Restored voice and video recording start notifications by monitoring Unigram's native recording UI, including recordings started manually."
) + "\n" + _(
	"- Ctrl+D now passes directly to Unigram for native voice-message cancellation, matching Ctrl+R."
) + "\n" + _(
	"- Fixed rich-message detection so sticker and emoji messages are no longer incorrectly announced as rich messages."
) + "\n" + _(
	"- Ctrl+R now uses Unigram's native voice-message recording and sending behavior while retaining UnigramPlus recording start and end notifications."
) + "\n" + _(
	"- Updated localizations."
)
