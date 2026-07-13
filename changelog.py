# A fake funct so that Gettext can search this file.
def _(t): return t

value = _(
	"Added support for rich messages. Rich messages are now announced when focused and can be opened with Alt+C in a browseable window."
) + " " + _(
	"Links and mixed content in rich messages are preserved, and links can be activated from the browseable window."
)
