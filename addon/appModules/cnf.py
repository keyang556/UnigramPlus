from  configobj  import  ConfigObj
from configobj.validate import Validator
import os
import globalVars
import languageHandler
import addonHandler
addonHandler.initTranslation()

listLanguages = {
	"ar": _("Arabic"),
	"be": _("Belarus"),
	"my": _("Burmese"),
	"cs": _("Czech"),
	"en": _("English"),
	"fr": _("French"),
	"fi": _("Finnish"),
	"sl": _("Slovak"),
	"nb": _("Norwegian"),
	"de": _("German"),
	"it": _("Italian"),
	"fa": _("Persian"),
	"pl": _("Polish"),
	"pt": _("Portuguese"),
	"ru": _("Russian"),
	"es": _("Spanish"),
	"tr": _("Turkish"),
	"uk": _("Ukrainian"),
	"hr": _("Croatian"),
	"sr": _("Serbian"),
	"zh_TW": _("Chinese (Traditional)"),
	"zh_CN": _("Chinese (Simplified)"),
	"ro": _("Romanian"),
}

def getDefaultLang():
	lang = languageHandler.getLanguage()
	if lang in listLanguages:
		return lang
	baseLang = lang.split("_")[0]
	return baseLang if baseLang in listLanguages else "en"

lang = getDefaultLang()

spec = (
	f"lang = string(default={lang if lang in listLanguages else 'en'})",
	"voiceTypeAfterChatName = string(default=beforeName)",
	"unreadBeforeMessageContent = boolean(default=True)",
	"voiceFolderNames = boolean(default=True)",
	"voiceMessageRecordingIndicator = string(default=audio)",
	"voicingPerformanceIndicators = string(default=upload_download)",
	"fileTransferProgressInterval = integer(default=1, min=1, max=100)",
	# One-shot marker so we can migrate users who had the old default of "none" to
	# the new "upload_download" mode the first time they launch 5.5.3.
	"voicingPerformanceIndicators_migrated_5_5_3 = boolean(default=False)",
	"audioPlaybackWhenDeleted = boolean(default=False)",
	"confirmation_at_deletion = boolean(default=False)",
	"actionDescriptionForLinks = boolean(default=True)",
	"voiceFullDescriptionOfLinkToYoutube = boolean(default=True)",
	"isAnnouncesAnswers = boolean(default=True)",
	"is_automatically_check_for_updates = boolean(default=True)",
	"isFixedToggleButton = boolean(default=False)",
	"saySenderName = string(default=none)",
	"voice_the_presence_of_a_reaction = boolean(default=True)",
	"report premium accounts = boolean(default=True)",
	"automatically announce new messages = boolean(default=False)",
	"automatically announce activity in chats = boolean(default=False)",
	"notify administrators in messages = boolean(default=True)",
	"action_when_pressing_up_arrow_in_text_field = string(default=normal)",
	"announce_endthe_message = boolean(default=True)",
	"play_typing_sound = boolean(default=True)"
)

class cnf:
	def __init__(self):
		self.path = os.path.join(globalVars.appArgs.configPath, "UnigramPlus.ini")
		self.conf = ConfigObj(self.path, configspec=spec )
		validator = Validator()
		self.conf.validate(validator, copy=True)
		if self.conf.get("lang") == "zh":
			self.conf["lang"] = "zh_TW"
		self.conf.write()
	def get(self, key):
		return self.conf[key]
	def set(self, key, value):
		self.conf[key] = value
		self.conf.write()

try: conf = cnf()
except Exception:
	from logHandler import log
	log.error("UnigramPlus.ini could not be loaded", exc_info=True)
	path = os.path.join(globalVars.appArgs.configPath, "UnigramPlus.ini")
	# Only treat this as a corrupt ini and rebuild from defaults if the file
	# itself fails to parse. If parsing succeeds, the failure was something
	# else (e.g. a permissions error on write), and deleting a valid,
	# user-edited config would just lose their settings without fixing anything.
	try:
		ConfigObj(path, configspec=spec)
	except Exception:
		if os.path.exists(path):
			os.remove(path)
		conf = cnf()
	else:
		raise
