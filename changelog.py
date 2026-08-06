# A fake funct so that Gettext can search this file.
def _(t): return t

value = _(
	"- Fixed Ctrl+Alt+Left/Right so they seek the current voice message playback again.\n"
	"- Fixed Alt+I so it moves to Unigram's inline chat search results list.\n"
	"- Added Alt+[ to announce message headers after the content, so file names can be announced before sender names in profile media sections."
)
