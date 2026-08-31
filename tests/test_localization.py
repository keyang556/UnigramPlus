import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOCALE_DIR = ROOT / "addon" / "locale"
DOC_DIR = ROOT / "addon" / "doc"
VERSION_REPORT = "Unigram version: {unigramVersion}. UnigramPlus version: {addonVersion}."

# Only active runtime strings belong here. Historical release notes and removed
# features may correctly be absent from the newest translator-maintained catalogs.
REQUIRED_TRANSLATIONS = {
	"Interface language in Unigram:",
	"Speak the type of chat in the chat list:",
	"Automatically move focus to the chat list when Unigram starts",
	"Say the sender's name in:",
	"Set voice message recording notification method as:",
	"Select the progress bar notification level:",
	"File transfer progress announcement interval (percent):",
	"Rich message",
	"Move to the next or previous chat with unread mentions",
	"No more chats with unread mentions in this direction",
	"No search results",
	"Toggle whether message headers are announced before or after the message content",
	"Message headers will be announced after the message content",
	"Message headers will be announced before the message content",
	"Announce message headers after the message content",
	"Play a sound when reaching the end of a chat",
	"Announce the Unigram and UnigramPlus version numbers",
	VERSION_REPORT,
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
		for placeholder in ("{unigramVersion}", "{addonVersion}"):
			assert placeholder in entries[VERSION_REPORT], (
				f"{locale_dir.name} version report is missing {placeholder}"
			)


def test_release_version_is_569():
	build_vars = (ROOT / "buildVars.py").read_text(encoding="utf-8")
	manifest = (ROOT / "addon" / "manifest.ini").read_text(encoding="utf-8")
	pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
	lockfile = (ROOT / "uv.lock").read_text(encoding="utf-8")

	assert 'addon_version="5.6.9"' in build_vars
	assert "version = 5.6.9" in manifest
	assert 'version = "5.6.9"' in pyproject
	assert 'name = "unigramplus"\nversion = "5.6.9"' in lockfile


def test_catalogs_keep_the_568_translation_metadata():
	for locale_dir in sorted(path for path in LOCALE_DIR.iterdir() if path.is_dir()):
		catalog = (locale_dir / "LC_MESSAGES" / "nvda.po").read_text(encoding="utf-8")
		assert '"Project-Id-Version: UnigramPlus 5.6.8\\n"' in catalog


def test_current_release_changelog_comes_from_the_changelog_source():
	changelog = (ROOT / "changelog.py").read_text(encoding="utf-8")

	assert "secure desktop" in changelog
	assert "Saved Messages topic name workaround" in changelog
	assert "NVDA 2026.2" in changelog
	assert "Polish and Burmese translations" in changelog


def test_every_localized_manual_has_569_through_559_and_updated_558_changelogs():
	manuals = [ROOT / "readme.md", *sorted(DOC_DIR.glob("*/readme.md"))]
	assert len(manuals) == 17
	for manual in manuals:
		text = manual.read_text(encoding="utf-8")
		version_569 = text.index("5.6.9")
		version_568 = text.index("5.6.8", version_569)
		version_567 = text.index("5.6.7", version_568)
		version_566 = text.index("5.6.6", version_567)
		version_565 = text.index("5.6.5", version_566)
		version_564 = text.index("5.6.4", version_565)
		version_563 = text.index("5.6.3", version_564)
		version_562 = text.index("5.6.2", version_563)
		version_561 = text.index("5.6.1", version_562)
		version_560 = text.index("5.6.0", version_561)
		version_559 = text.index("5.5.9", version_560)
		version_558 = text.index("5.5.8", version_559)
		section_569 = text[version_569:version_568]
		section_568 = text[version_568:version_567]
		section_567 = text[version_567:version_566]
		section_566 = text[version_566:version_565]
		section_565 = text[version_565:version_564]
		section_564 = text[version_564:version_563]
		section_563 = text[version_563:version_562]
		section_562 = text[version_562:version_561]
		section_561 = text[version_561:version_560]
		section_560 = text[version_560:version_559]
		assert section_569.count("\n* ") == 5, manual
		assert "Alt+C" in section_568, manual
		assert "WhatsApp Enhancer" in section_568, manual
		assert section_568.count("\n* ") == 1, manual
		assert "NVDA+Alt+V" in section_567, manual
		assert "Shift+Delete" in section_567 or "Shift+Suppr" in section_567, manual
		assert section_567.count("\n* ") == 2, manual
		assert "NVDA+Shift+V" in section_566 or "NVDA+Maj+V" in section_566, manual
		assert "12.9.1" in section_566, manual
		assert section_566.count("\n* ") == 3, manual
		assert "Enter" in section_565 or "Entrée" in section_565, manual
		assert "Alt+Shift+R" in section_565 or "Alt+Maj+R" in section_565, manual
		assert "Alt+C" in section_565, manual
		assert section_565.count("\n* ") == 3, manual
		assert "Shift+Delete" in section_564, manual
		assert "Alt+2" in section_564, manual
		assert "Alt+C" in section_564, manual
		assert "12.9" in section_564, manual
		assert section_564.count("\n* ") == 6, manual
		assert "NVDA" in section_563, manual
		assert "Alt+[" in section_563, manual
		assert section_563.count("\n* ") == 3, manual
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


def test_removed_web_view_setting_is_absent_but_historical_changelogs_remain():
	setting = "Display message text in a web view when pressing Alt+C"
	runtime_hint = "Rich message. Press Alt+C to browse"
	for locale_dir in sorted(path for path in LOCALE_DIR.iterdir() if path.is_dir()):
		entries = _parse_po(locale_dir / "LC_MESSAGES" / "nvda.po")
		assert setting not in entries, locale_dir
		assert runtime_hint not in entries, locale_dir
	manuals = [ROOT / "readme.md", *sorted(DOC_DIR.glob("*/readme.md"))]
	for manual in manuals:
		text = manual.read_text(encoding="utf-8")
		section_564 = text[text.index("5.6.4"):text.index("5.6.3", text.index("5.6.4"))]
		section_559 = text[text.index("5.5.9"):text.index("5.5.8", text.index("5.5.9"))]
		assert "Alt+C" in section_564, manual
		assert "Alt+C" in section_559, manual
