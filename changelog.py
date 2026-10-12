# A fake funct so that Gettext can search this file.
def _(t): return t

value = _(
	"""- Removed UnigramPlus's own Enter and Space handling in the list of Unigram settings categories: in Unigram 13.0 and later, the categories are buttons that open with these keys themselves. Enter and Space are also no longer intercepted on other tabs, such as the Emoji, GIFs and Stickers tabs.
- In Unigram settings, Alt+1 now moves the focus to the open settings category.
- Removed code that could no longer run: name replacements for list items from Unigram versions before 9.5, and the quiz explanation window disabled since version 5.2.0.
- Updated the Polish and Vietnamese translations."""
)
