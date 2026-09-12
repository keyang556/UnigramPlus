# A fake funct so that Gettext can search this file.
def _(t): return t

value = _(
	"""- Background checks no longer run on NVDA's main loop, so chat navigation and speech are no longer held up.
- Every behavior added after 5.4 can now be turned on or off in UnigramPlus settings.
- Fixed the space bar not playing voice messages and music, Enter not replying, ALT+E not closing the audio player, and Ctrl+ALT+Left/Right not seeking."""
)
