# A fake funct so that Gettext can search this file.
def _(t): return t

value = _(
	"""- Removed the call duration workaround: Unigram 12.10 and later announce a call message's duration themselves, so it is no longer announced twice.
- Fixed the add-on failing to start on older NVDA versions that do not provide the utils.security module.
- Updated the Vietnamese translation."""
)
