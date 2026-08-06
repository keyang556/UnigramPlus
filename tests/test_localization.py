import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOCALE_DIR = ROOT / "addon" / "locale"
DOC_DIR = ROOT / "addon" / "doc"

REQUIRED_TRANSLATIONS = {
	"Interface language in Unigram:",
	"Speak the type of chat in the chat list:",
	"Automatically move focus to the chat list when Unigram starts",
	"Say the sender's name in:",
	"Set voice message recording notification method as:",
	"Select the progress bar notification level:",
	"File transfer progress announcement interval (percent):",
	"Rich message",
	"Rich message. Press Alt+C to browse",
	"Added support for rich messages. Rich messages are now announced when focused and can be opened with Alt+C in a browseable window.",
	"Links and mixed content in rich messages are preserved, and links can be activated from the browseable window.",
	"Fixed automatic updates: releases are now retrieved securely from GitHub and the downloaded add-on is validated before installation.",
	"Move to the next or previous chat with unread mentions",
	"No more chats with unread mentions in this direction",
	"No search results",
	"Toggle whether message headers are announced before or after the message content",
	"Message headers will be announced after the message content",
	"Message headers will be announced before the message content",
	(
		"- Fixed Ctrl+Alt+Left/Right so they seek the current voice message playback again.\n"
		"- Fixed Alt+I so it moves to Unigram's inline chat search results list.\n"
		"- Added Alt+[ to announce message headers after the content, so file names can be announced before sender names in profile media sections."
	),
}


def _parse_po(path: Path) -> dict[str, str]:
	"""Return singular, non-obsolete gettext entries without external dependencies."""
	entries: dict[str, str] = {}
	msgid_parts: list[str] = []
	msgstr_parts: list[str] = []
	state = None

	def finish_entry():
		if msgid_parts:
			entries["".join(msgid_parts)] = "".join(msgstr_parts)

	for line in path.read_text(encoding="utf-8").splitlines() + [""]:
		if not line:
			finish_entry()
			msgid_parts.clear()
			msgstr_parts.clear()
			state = None
			continue
		if line.startswith("#~"):
			continue
		if line.startswith("msgid "):
			msgid_parts.append(ast.literal_eval(line[6:]))
			state = "msgid"
		elif line.startswith("msgstr "):
			msgstr_parts.append(ast.literal_eval(line[7:]))
			state = "msgstr"
		elif line.startswith('"') and state == "msgid":
			msgid_parts.append(ast.literal_eval(line))
		elif line.startswith('"') and state == "msgstr":
			msgstr_parts.append(ast.literal_eval(line))
	return entries


def test_required_strings_are_translated_in_every_locale():
	locale_dirs = sorted(path for path in LOCALE_DIR.iterdir() if path.is_dir())
	assert len(locale_dirs) == 19
	for locale_dir in locale_dirs:
		entries = _parse_po(locale_dir / "LC_MESSAGES" / "nvda.po")
		missing = sorted(key for key in REQUIRED_TRANSLATIONS if not entries.get(key))
		assert not missing, f"{locale_dir.name} has missing translations: {missing}"


def test_release_version_is_562():
	build_vars = (ROOT / "buildVars.py").read_text(encoding="utf-8")
	manifest = (ROOT / "addon" / "manifest.ini").read_text(encoding="utf-8")
	pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

	assert 'addon_version="5.6.2"' in build_vars
	assert "version = 5.6.2" in manifest
	assert 'version = "5.6.2"' in pyproject


def test_every_localized_manual_has_562_561_560_559_and_updated_558_changelogs():
	manuals = [ROOT / "readme.md", *sorted(DOC_DIR.glob("*/readme.md"))]
	assert len(manuals) == 17
	for manual in manuals:
		text = manual.read_text(encoding="utf-8")
		version_562 = text.index("5.6.2")
		version_561 = text.index("5.6.1", version_562)
		version_560 = text.index("5.6.0", version_561)
		version_559 = text.index("5.5.9", version_560)
		version_558 = text.index("5.5.8", version_559)
		section_562 = text[version_562:version_561]
		section_561 = text[version_561:version_560]
		section_560 = text[version_560:version_559]
		assert "Ctrl+Alt+Left/Right" in section_562, manual
		assert "Alt+I" in section_562, manual
		assert "Alt+[" in section_562, manual
		assert section_562.count("\n* ") == 3, manual
		assert "Ctrl+Alt+Up/Down" in section_561, manual
		assert section_561.count("\n* ") == 3, manual
		assert "Ctrl+R" in section_560, manual
		assert section_560.count("\n* ") == 3, manual
		assert "Alt+C" in text[version_559:version_558], manual
		assert "GitHub" in text[version_558:text.find("5.5.7", version_558)], manual
