# A fake funct so that Gettext can search this file.
def _(t): return t

value = _(
	"This release restores compatibility with Unigram 12.7, where several shortcuts and announcements had stopped working."
) + " " + _(
	"Poll messages again announce the question and answer options, and the forum topic list again announces the message preview."
) + " " + _(
	"During a one-to-one call, the mute microphone (ALT+A), enable or disable camera (ALT+V) and end call (ALT+N) shortcuts work again, and ALT+End again moves to the latest message."
)
