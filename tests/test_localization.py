import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOCALE_DIR = ROOT / "addon" / "locale"
DOC_DIR = ROOT / "addon" / "doc"
VERSION_REPORT = "Unigram version: {unigramVersion}.\nUnigramPlus version: {addonVersion}."
VERSION_WINDOW_DESCRIPTION = "Open Unigram and UnigramPlus version information in a read-only window"
RELEASE_CHANGELOG = (
	"""- Fixed NVDA errors with the Unigram WinUI 3 beta each time you switched back to Unigram or typed with an input method (IME).
- UnigramPlus no longer interferes with focus announcements in Telegram Desktop when the Telegram Desktop add-on is not installed.
- Removed the notification when a voice or video message recording is canceled: Unigram 13.0 and later announce it themselves, so it is no longer heard twice.
- Updated the Polish and Vietnamese translations."""
)
RECORDING_NOTIFICATION_LABEL = "Notification when a voice message recording starts or is sent:"

# The voice recording feature bullet said canceling was accompanied by a sound
# until Unigram 13.0 started announcing a canceled recording itself. Keyed by
# manual language; the root readme.md mirrors the English one.
RECORDING_CANCELED_FEATURE = {
	"en": "Recording, sending and canceling",
	"NE": "रेकर्ड गर्ने, पठाउने र रद्दगर्दा",
	"ar": "وإلغاء تسجيلها",
	"es": "envío y cancelación de mensajes de voz",
	"fa": "ضبط، ارسال و لغو ضبط",
	"fr": "l'envoi et l'annulation de l'enregistrement",
	"hr": "Snimanje, slanje i otkazivanje",
	"pt_BR": "gravar, enviar e cancelar",
	"pt_PT": "gravar, enviar e cancelar",
	"ro": "trimiterea și anularea înregistrării",
	"ru": "Запись, отправка и отмена записи",
	"sr": "i otkazivanje snimanja popraćeni",
	"tr": "kayıt iptaline farklı sesler",
	"uk": "Запис, надсилання та скасування запису",
	"zh_CN": "录制、发送和取消语音消息",
	"zh_TW": "錄製、傳送與取消語音訊息",
}

# The call duration feature bullet each manual carried before Unigram 12.10
# started announcing it natively. Keyed by manual language; the root readme.md
# mirrors the English one.
CALL_DURATION_FEATURE = {
	"en": "the duration of this call is announced",
	"NE": "कलको अवधि समेत घोषणा",
	"ar": "يتم الإعلان عن مدة هذه المكالمة",
	"es": "se anuncia la duración de dicha llamada",
	"fa": "مدت زمان این تماس اعلام می شود",
	"fr": "la durée de celui-ci est annoncée",
	"hr": "najavljuje se trajanje tog poziva",
	"pt_BR": "a duração dessa chamada é anunciada",
	"pt_PT": "a duração dessa chamada é anunciada",
	"ro": "se anunță durata acestui apel",
	"ru": "объявляется продолжительность этого звонка",
	"sr": "objavljuje se trajanje tog poziva",
	"tr": "bu çağrının süresi duyulur",
	"uk": "озвучується тривалість цьього дзвінка",
	# Chinese stated it inside a combined sentence, so the removed words are the marker.
	"zh_CN": "通话消息",
	"zh_TW": "通話訊息",
}

# Only active runtime strings belong here. Historical release notes and removed
# features may correctly be absent from the newest translator-maintained catalogs.
REQUIRED_TRANSLATIONS = {
	"Interface language in Unigram:",
	"Speak the type of chat in the chat list:",
	"Automatically move focus to the chat list when Unigram starts",
	"Say the sender's name in:",
	RECORDING_NOTIFICATION_LABEL,
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
	VERSION_WINDOW_DESCRIPTION,
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
	assert len(locale_dirs) == 20
	for locale_dir in locale_dirs:
		entries = _parse_po(locale_dir / "LC_MESSAGES" / "nvda.po")
		missing = sorted(key for key in REQUIRED_TRANSLATIONS if not entries.get(key))
		assert not missing, f"{locale_dir.name} has missing translations: {missing}"
		for placeholder in ("{unigramVersion}", "{addonVersion}"):
			assert placeholder in entries[VERSION_REPORT], (
				f"{locale_dir.name} version report is missing {placeholder}"
			)
		assert "\n" in entries[VERSION_REPORT], (
			f"{locale_dir.name} version report does not put UnigramPlus on a new line"
		)


def test_release_version_is_582():
	build_vars = (ROOT / "buildVars.py").read_text(encoding="utf-8")
	pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
	lockfile = (ROOT / "uv.lock").read_text(encoding="utf-8")

	assert 'addon_version="5.8.2"' in build_vars
	assert 'version = "5.8.2"' in pyproject
	assert 'name = "unigramplus"\nversion = "5.8.2"' in lockfile

	# addon/manifest.ini is a gitignored build artifact and may be stale, so the
	# template is what gets checked: it is what carries addon_version into the build.
	template = (ROOT / "manifest.ini.tpl").read_text(encoding="utf-8")
	assert "version = {addon_version}" in template


def test_catalogs_keep_the_582_translation_metadata():
	for locale_dir in sorted(path for path in LOCALE_DIR.iterdir() if path.is_dir()):
		catalog_path = locale_dir / "LC_MESSAGES" / "nvda.po"
		catalog = catalog_path.read_text(encoding="utf-8")
		assert '"Project-Id-Version: UnigramPlus 5.8.2\\n"' in catalog


def test_current_release_changelog_comes_from_the_changelog_source():
	changelog = (ROOT / "changelog.py").read_text(encoding="utf-8")

	assert "WinUI 3" in changelog
	assert "Telegram Desktop add-on" in changelog
	assert "Unigram 13.0" in changelog


def test_every_catalog_translates_the_current_release_changelog():
	for locale_dir in sorted(path for path in LOCALE_DIR.iterdir() if path.is_dir()):
		entries = _parse_po(locale_dir / "LC_MESSAGES" / "nvda.po")
		assert entries.get(RELEASE_CHANGELOG), locale_dir.name


def test_the_english_manual_carries_the_current_release():
	for manual in (ROOT / "readme.md", DOC_DIR / "en" / "readme.md"):
		text = manual.read_text(encoding="utf-8")
		version_582 = text.index("5.8.2")
		version_581 = text.index("5.8.1", version_582)
		section_582 = text[version_582:version_581]
		assert section_582.count("\n* ") == 4, manual
		assert "WinUI 3" in section_582, manual
		assert "Since version 5.5.6" in section_582, manual
		assert "Telegram Desktop add-on" in section_582, manual
		assert "Unigram 13.0" in section_582, manual
		assert RECORDING_NOTIFICATION_LABEL.rstrip(":") in section_582, manual
		assert "Polish and Vietnamese" in section_582, manual
		version_581 = text.index("5.8.1")
		version_580 = text.index("5.8.0", version_581)
		section_581 = text[version_581:version_580]
		section_580 = text[version_580:text.index("5.7.3", version_580)]
		assert section_581.count("\n* ") == 4, manual
		assert "call duration workaround" in section_581, manual
		assert "utils.security" in section_581, manual
		assert section_580.count("\n* ") == 10, manual
		assert "main loop" in section_580, manual
		assert "version 5.4" in section_580, manual


def test_every_localized_manual_has_582_581_and_580_changelogs():
	manuals = [ROOT / "readme.md", *sorted(DOC_DIR.glob("*/readme.md"))]
	assert len(manuals) == 17
	for manual in manuals:
		text = manual.read_text(encoding="utf-8")
		version_582 = text.index("5.8.2")
		section_582 = text[version_582:text.index("5.8.1", version_582)]
		assert section_582.count("\n* ") == 4, manual
		for marker in ("WinUI 3", "5.5.6", "IME", "UWP", "Telegram Desktop", "13.0", "Ctrl+D"):
			assert marker in section_582, (manual, marker)
		version_581 = text.index("5.8.1")
		version_580 = text.index("5.8.0", version_581)
		version_573 = text.index("5.7.3", version_580)
		assert text[version_581:version_580].count("\n* ") == 4, manual
		assert text[version_580:version_573].count("\n* ") == 10, manual
		assert "12.10" in text[version_581:version_580], manual
		assert "utils.security" in text[version_581:version_580], manual


def test_the_call_duration_workaround_is_gone_everywhere():
	"""Unigram 12.10 names the duration itself, so the add-on must not add it."""
	source = (ROOT / "addon" / "appModules" / "unigram.py").read_text(encoding="utf-8-sig")
	assert "Checking if a message is a call" not in source

	for manual in [ROOT / "readme.md", *sorted(DOC_DIR.glob("*/readme.md"))]:
		language = "en" if manual.parent == ROOT else manual.parent.name
		text = manual.read_text(encoding="utf-8")
		# Everything before the current release notes: the feature list, the
		# shortcut tables and every historical changelog entry. The phrase only
		# ever appeared in the feature list, so it must not appear here at all.
		# The 5.8.1 notes themselves do describe the removal, in Chinese using
		# the same words, which is why they are excluded.
		assert CALL_DURATION_FEATURE[language] not in text[:text.index("5.8.1")], manual


def test_feature_lists_leave_canceled_recordings_to_unigram():
	"""Unigram 13.0 announces a canceled recording, so the add-on no longer claims to."""
	for manual in [ROOT / "readme.md", *sorted(DOC_DIR.glob("*/readme.md"))]:
		language = "en" if manual.parent == ROOT else manual.parent.name
		text = manual.read_text(encoding="utf-8")
		# The feature list ends at the first ### heading. Older release notes,
		# which some manuals keep above 5.8.2, still describe the sound.
		features = text[:text.index("###")]
		assert RECORDING_CANCELED_FEATURE[language] not in features, manual
		assert "Unigram 13.0" in features, manual


def test_every_localized_manual_has_573_through_559_and_updated_558_changelogs():
	manuals = [ROOT / "readme.md", *sorted(DOC_DIR.glob("*/readme.md"))]
	assert len(manuals) == 17
	for manual in manuals:
		text = manual.read_text(encoding="utf-8")
		version_573 = text.index("5.7.3")
		version_572 = text.index("5.7.2", version_573)
		version_571 = text.index("5.7.1", version_572)
		version_570 = text.index("5.7.0", version_571)
		version_569 = text.index("5.6.9", version_570)
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
		section_573 = text[version_573:version_572]
		section_572 = text[version_572:version_571]
		section_571 = text[version_571:version_570]
		section_570 = text[version_570:version_569]
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
		assert section_573.count("\n* ") == 1, manual
		assert "NVDA+Alt+V" in section_573, manual
		assert section_572.count("\n* ") == 1, manual
		assert "NVDA+Alt+V" in section_572, manual
		assert section_571.count("\n* ") == 1, manual
		assert "12.10.2" in section_571, manual
		assert section_570.count("\n* ") == 2, manual
		assert "12.10.1+" in section_569, manual
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


def test_every_manual_still_documents_the_file_duration_it_does_announce():
	"""The audio file's own duration is a separate, still-present feature."""
	kept = {
		"en": "name and duration",
		"es": "nombre y duración",
		"fr": "son nom et sa durée",
		"hr": "naziv i trajanje",
		"ro": "numele și durata",
		"ru": "название и продолжительность",
		"uk": "назва і тривалість",
	}
	for language, phrase in kept.items():
		manual = ROOT / "readme.md" if language == "en" else DOC_DIR / language / "readme.md"
		assert phrase in manual.read_text(encoding="utf-8"), language


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
