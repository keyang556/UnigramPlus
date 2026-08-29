# -*- coding:utf-8 -*-
from NVDAObjects.UIA import ListItem
import winUser
import mouseHandler
from keyboardHandler import KeyboardInputGesture
import appModuleHandler
import core
from ui import message
import api
from controlTypes import Role, State
import scriptHandler
from scriptHandler import script
from NVDAObjects.UIA import UIA
import languageHandler
import addonHandler
import textInfos
import editableText
addonHandler.initTranslation()
import speech
from  threading import Timer
import time
import winsound
from nvwave import playWaveFile
import os
import globalVars
from logHandler import log
import queueHandler
import sys
import re
import importlib.util
sys.path.insert(0, ".")
from .data import *
from .unigramplus_text_window import TextWindow
from .cnf import conf, lang
from .readme_shortcuts import extractShortcutText  # noqa: E402
from .message_header import (  # noqa: E402
	move_message_header_after_content,
	move_profile_header_after_content,
)
from .rich_message import (  # noqa: E402
	extract_message_text,
	extract_rich_message_text,
	find_rich_message_root,
	merge_message_text_and_rich_text,
)
from .voice_recording import (  # noqa: E402
	VoiceRecordingOutcome,
	VoiceRecordingState,
	is_recorded_message,
	is_recording_button,
	message_marker,
	recording_button_state,
)

baseDir = os.path.join(os.path.dirname(__file__), "media\\")
_END_OF_CHAT_SOUND_FILENAME = "EndOfChatDefault.wav"
_END_OF_CHAT_CUSTOM_SOUND_FILENAME = "UnigramEndOfChat.wav"
_telegramDesktopFallbackClass = None
_telegramDesktopFallbackLoadAttempted = False

_APP_MODULE_NAME_IGNORED_CHARS = str.maketrans("", "", "\u200e\u200f\u2066\u2067\u2068\u2069")
_VOICE_RECORDING_POLL_INTERVAL = .2
# Allow Unigram time to finalize the recording and insert its outgoing message.
# A sent message is still reported immediately; only cancellation waits this long.
_VOICE_RECORDING_OUTCOME_POLL_LIMIT = 25  # 5 seconds at the interval above.
_AUTO_FOCUS_CHAT_LIST_DELAY_MS = 300
_AUTO_FOCUS_CHAT_LIST_RETRY_LIMIT = 10
_END_OF_CHAT_PROBE_DELAY_MS = 50
_SEARCH_RESULT_COUNTER_RE = re.compile(r"^\s*(\d+)\s*/\s*(\d+)\s*$")
_SEARCH_RESULT_COUNTER_SIBLING_LIMIT = 6
_CONTEXT_MENU_STEP_DELAY_MS = 20
_CONTEXT_MENU_NAVIGATION_DELAY_MS = 250
_CONTEXT_MENU_OPEN_TIMEOUT_MS = 10000
_CONTEXT_MENU_ACTIVITY_TIMEOUT_MS = 3000
_CONTEXT_MENU_NAVIGATION_LIMIT = 30
_CONTEXT_MENU_RAW_PROBE_DELAY_MS = 50
_CONTEXT_MENU_RAW_RETRY_DELAY_MS = 150
# Message_ContextRequested awaits GetMessageProperties before Unigram creates the
# flyout. Keep the cheap focused-element poll alive for almost the entire open
# timeout so a slow TDLib response does not make the shortcut probabilistic.
_CONTEXT_MENU_RAW_PROBE_LIMIT = (_CONTEXT_MENU_OPEN_TIMEOUT_MS // _CONTEXT_MENU_RAW_RETRY_DELAY_MS) + 1
_CONTEXT_MENU_RAW_SCOPE_LIMIT = 6
_CONTEXT_MENU_RAW_ITEM_DEPTH_LIMIT = 10
_CONTEXT_MENU_RAW_TEXT_LIMIT = 64
_MAIN_WINDOW_AUTOMATION_IDS = frozenset(("ChatsList", "Messages", "TextField", "Navigation"))
_CALL_WINDOW_AUTOMATION_IDS = frozenset(("ActiveButtons", "BottomRoot"))
_WINDOW_SURFACE_AUTOMATION_IDS = _MAIN_WINDOW_AUTOMATION_IDS | _CALL_WINDOW_AUTOMATION_IDS


def _get_end_of_chat_sound_path():
	"""Return the user override when present, otherwise the bundled sound."""
	try:
		custom_sound = os.path.join(
			globalVars.appArgs.configPath,
			_END_OF_CHAT_CUSTOM_SOUND_FILENAME,
		)
		if os.path.isfile(custom_sound):
			return custom_sound
	except Exception:
		# Falling back to the bundled asset keeps this non-essential notification
		# from affecting message navigation if the configuration path is unavailable.
		pass
	return os.path.join(baseDir, _END_OF_CHAT_SOUND_FILENAME)


def play_end_of_chat_sound():
	"""Play the optional notification that indicates the last chat message."""
	if not conf.get("play_end_of_chat_sound"):
		log.debug("End-of-chat sound is disabled in UnigramPlus settings")
		return False
	try:
		sound_path = _get_end_of_chat_sound_path()
		log.debug("Playing end-of-chat sound from %r", sound_path)
		# Match RussianMod's proven playback path. NVDA's global file wave player
		# can be preempted by speech-related sounds before this short cue is heard.
		winsound.PlaySound(sound_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
		return True
	except Exception:
		log.debug("Could not play end-of-chat sound", exc_info=True)
		return False


def _normalized_text(text):
	try: text = text or ""
	except Exception: text = ""
	return str(text).translate(_APP_MODULE_NAME_IGNORED_CHARS).strip().casefold()


def _context_menu_raw_probe_hint_priority(obj):
	"""Rank popup hints so a generic app window cannot replace a flyout root."""
	if obj is None:
		return -1
	identity = []
	for attribute in ("UIAClassName", "UIAAutomationId"):
		try:
			identity.append(str(getattr(obj, attribute, "") or "").casefold())
		except Exception:
			pass
	identity = " ".join(identity)
	if any(marker in identity for marker in ("popup", "flyout", "menu")):
		return 2
	try:
		name = str(getattr(obj, "name", "") or "").strip().casefold()
	except Exception:
		name = ""
	if name in ("unigram", "telegram"):
		return 0
	return 1


def _walk_bounded_descendants(root, max_nodes=100):
	"""Yield a small UIA subtree without trusting provider parent/child links."""
	try:
		pending = list(root.children or ())
	except Exception:
		pending = []
	seen = {id(root)}
	visited = 0
	while pending and visited < max_nodes:
		node = pending.pop(0)
		identity = id(node)
		if identity in seen:
			continue
		seen.add(identity)
		visited += 1
		yield node
		try:
			pending.extend(node.children or ())
		except Exception:
			pass


def _menu_item_has_icon(item, icons):
	"""Match an icon within one menu item's small Raw UIA subtree."""
	if isinstance(icons, str):
		icons = (icons,)
	icons = frozenset(icons)
	for node in (item, *_walk_bounded_descendants(item, max_nodes=20)):
		try:
			name = str(node.name or "")
			if any(icon in name for icon in icons):
				return True
		except Exception:
			pass
	return False


def _raw_uia_property(element, property_id):
	"""Read one raw UIA property without assuming the element has a cache."""
	if property_id is None:
		return None
	for method_name, arguments in (
		("GetCachedPropertyValueEx", (property_id, True)),
		("GetCurrentPropertyValueEx", (property_id, True)),
		("GetCurrentPropertyValue", (property_id,)),
	):
		try:
			return getattr(element, method_name)(*arguments)
		except Exception:
			continue
	return None


def _raw_uia_text(element):
	"""Read a short TextPattern value from a raw XAML element, when available."""
	import UIAHandler

	available = _raw_uia_property(
		element,
		UIAHandler.UIA.UIA_IsTextPatternAvailablePropertyId,
	)
	if not available:
		return ""
	pattern = None
	for method_name in ("GetCachedPattern", "GetCurrentPattern"):
		try:
			pattern = getattr(element, method_name)(UIAHandler.UIA_TextPatternId)
			if pattern:
				break
		except Exception:
			continue
	if not pattern:
		return ""
	try:
		pattern = pattern.QueryInterface(UIAHandler.IUIAutomationTextPattern)
		return str(pattern.DocumentRange.GetText(_CONTEXT_MENU_RAW_TEXT_LIMIT) or "")
	except Exception:
		return ""


def _raw_menu_item_has_icon(item, icons, diagnose=False):
	"""Match a MenuFlyoutItem icon along Unigram's bounded first-child raw path."""
	import UIAHandler

	if isinstance(icons, str):
		icons = (icons,)
	icons = frozenset(icons)
	handler = UIAHandler.handler
	walker = handler.baseTreeWalker
	cache_request = handler.baseCacheRequest
	legacy_value_property = getattr(
		UIAHandler,
		"UIA_LegacyIAccessibleValuePropertyId",
		None,
	)
	property_ids = (
		UIAHandler.UIA.UIA_NamePropertyId,
		UIAHandler.UIA.UIA_ValueValuePropertyId,
		legacy_value_property,
	)
	element = item
	path = []
	for depth in range(_CONTEXT_MENU_RAW_ITEM_DEPTH_LIMIT):
		values = []
		for property_id in property_ids:
			value = _raw_uia_property(element, property_id)
			if isinstance(value, str) and value:
				values.append(value[:_CONTEXT_MENU_RAW_TEXT_LIMIT])
		text = _raw_uia_text(element)
		if text:
			values.append(text[:_CONTEXT_MENU_RAW_TEXT_LIMIT])
		if diagnose:
			class_name = _raw_uia_property(
				element,
				UIAHandler.UIA.UIA_ClassNamePropertyId,
			)
			automation_id = _raw_uia_property(
				element,
				UIAHandler.UIA.UIA_AutomationIdPropertyId,
			)
			control_type = _raw_uia_property(
				element,
				UIAHandler.UIA.UIA_ControlTypePropertyId,
			)
			path.append((depth, class_name, automation_id, control_type, values))
		if any(icon in value for icon in icons for value in values):
			if diagnose:
				log.debug("Matched raw Unigram menu icon %r at path %r", icons, path)
			return True
		try:
			element = walker.GetFirstChildElementBuildCache(element, cache_request)
		except Exception:
			break
		if not element:
			break
	if diagnose:
		log.debug("Raw Unigram MenuItem first-child path: %r", path)
	return False


def _find_raw_context_menu_item_by_icon(root, icons, process_id=0, diagnose=False):
	"""Find a popup command by its FontIcon without using translated labels."""
	from time import perf_counter

	import UIAHandler

	if isinstance(icons, str):
		icons = (icons,)
	client = UIAHandler.handler.clientObject
	walker = UIAHandler.handler.baseTreeWalker
	try:
		process_id = int(process_id or root.processID)
	except Exception:
		process_id = 0
	try:
		scope_root = root.UIAElement
	except Exception:
		scope_root = root
	for scope_depth in range(_CONTEXT_MENU_RAW_SCOPE_LIMIT):
		# Never issue FindAll from NVDA's desktop root. That crosses every UIA
		# provider and can leave the MTA worker blocked after Unigram closes its
		# popup. A few raw parents are enough to reach the common XAML ancestor of
		# ReactionsMenuFlyout's sibling reaction and command popups.
		try:
			if client.CompareElements(scope_root, UIAHandler.handler.rootElement):
				break
		except Exception:
			pass
		menu_item_condition = client.CreatePropertyCondition(
			UIAHandler.UIA.UIA_ControlTypePropertyId,
			UIAHandler.UIA.UIA_MenuItemControlTypeId,
		)
		if process_id:
			condition = client.CreateAndConditionFromArray(
				[
					menu_item_condition,
					client.CreatePropertyCondition(
						UIAHandler.UIA.UIA_ProcessIdPropertyId,
						process_id,
					),
				]
			)
		else:
			condition = menu_item_condition
		started = perf_counter()
		if diagnose:
			log.debug(
				"Querying raw Unigram MenuItems at popup scope depth %d",
				scope_depth,
			)
		try:
			menu_items = scope_root.findAll(UIAHandler.TreeScope_Descendants, condition)
		except Exception:
			if diagnose:
				log.debug(
					"Raw Unigram MenuItem query failed at popup scope depth %d",
					scope_depth,
					exc_info=True,
				)
			menu_items = None
		try:
			menu_item_count = menu_items.length if menu_items else 0
		except Exception:
			menu_item_count = 0
		if diagnose:
			log.debug(
				"Raw Unigram MenuItem query returned %d candidate(s) in %.3fs",
				menu_item_count,
				perf_counter() - started,
			)
		if menu_item_count:
			for index in range(menu_item_count):
				try:
					item = menu_items.getElement(index)
					if _raw_menu_item_has_icon(item, icons, diagnose):
						return item
				except Exception:
					# A transient XAML popup can disappear while its bounded item path
					# is inspected. Continue to another candidate in the same menu.
					continue
			# The nearest scope containing MenuItems is the command popup. Do not
			# widen the query into the main application after inspecting it.
			return None
		try:
			scope_root = walker.getParentElement(scope_root)
		except Exception:
			break
		if not scope_root:
			break
	return None


def _invoke_raw_context_menu_option(root, icons, process_id=0, diagnose=False):
	"""Invoke a raw UIA context-menu command identified by its Unigram icon."""
	import UIAHandler

	item = _find_raw_context_menu_item_by_icon(root, icons, process_id, diagnose)
	if not item:
		return False
	pattern = item.GetCurrentPattern(UIAHandler.UIA_InvokePatternId)
	if not pattern:
		return False
	pattern.QueryInterface(UIAHandler.IUIAutomationInvokePattern).Invoke()
	return True


def _get_raw_context_menu_focus(process_id=0):
	"""Return the raw focused popup control without depending on an NVDA event.

	NVDA maps UIA's MenuOpened event to gainFocus, but intentionally drops that
	event when another focus event is already pending. Reading UIA focus on the
	MTA thread lets the context-menu retry loop observe the opened XAML flyout even
	when the app module never receives a popup focus event.
	"""
	import UIAHandler

	handler = UIAHandler.handler
	client = handler.clientObject
	try:
		focused = client.GetFocusedElementBuildCache(handler.baseCacheRequest)
	except Exception:
		try:
			focused = client.GetFocusedElement()
		except Exception:
			return None
	if not focused:
		return None
	try:
		target_process_id = int(process_id or 0)
	except (TypeError, ValueError):
		return None
	try:
		focused_process_id = int(
			_raw_uia_property(focused, UIAHandler.UIA.UIA_ProcessIdPropertyId) or 0
		)
	except Exception:
		focused_process_id = 0
	if target_process_id and focused_process_id != target_process_id:
		return None
	control_type = _raw_uia_property(
		focused,
		UIAHandler.UIA.UIA_ControlTypePropertyId,
	)
	popup_control_types = frozenset(
		control_type_id
		for control_type_id in (
			getattr(UIAHandler.UIA, "UIA_MenuItemControlTypeId", None),
			getattr(UIAHandler.UIA, "UIA_MenuControlTypeId", None),
			getattr(UIAHandler.UIA, "UIA_HyperlinkControlTypeId", None),
			getattr(UIAHandler.UIA, "UIA_ButtonControlTypeId", None),
			getattr(UIAHandler.UIA, "UIA_WindowControlTypeId", None),
		)
		if control_type_id is not None
	)
	return focused if control_type in popup_control_types else None


def _find_ancestor_by_automation_id(obj, automation_ids, max_depth=6):
	"""Find a named UIA ancestor without materializing any sibling subtrees."""
	seen = set()
	for _ in range(max_depth + 1):
		if not obj or id(obj) in seen:
			return None
		seen.add(id(obj))
		try:
			automation_id = obj.UIAAutomationId
		except Exception:
			automation_id = ""
		if automation_id in automation_ids:
			return obj
		try:
			obj = obj.parent
		except Exception:
			return None
	return None


def _is_message_list_item(obj):
	"""Recognize the focused message control exposed by current and older Unigram."""
	try:
		if obj.role != Role.LISTITEM:
			return False
		automation_id = str(getattr(obj, "UIAAutomationId", "") or "")
		if automation_id == "Message_item":
			# Preserve the exact marker used by released Unigram versions.
			return True
		class_name = (
			str(getattr(obj, "UIAClassName", "") or "")
			.replace(":", ".")
			.rsplit(".", 1)[-1]
		)
		if automation_id != "MessageSelector" and class_name != "MessageSelector":
			return False
		return _find_ancestor_by_automation_id(obj, ("Messages",), max_depth=8) is not None
	except Exception:
		return False


def _is_chat_list_item(obj):
	"""Recognize a chat row through Unigram's stable ChatsList boundary."""
	try:
		return (
			obj.role == Role.LISTITEM
			and _find_ancestor_by_automation_id(obj, ("ChatsList",), max_depth=8) is not None
		)
	except Exception:
		return False


def _announce_call_state_later(text, delay_ms=150):
	"""Announce a call-control state from NVDA's main event loop.

	``threading.Timer`` runs callbacks on a native thread. Calling NVDA's UI and
	speech APIs there can deadlock while Unigram is raising UIA events, which is
	particularly likely when a call control changes state.
	"""
	try:
		import core
		core.callLater(delay_ms, message, text)
	except Exception:
		# This fallback still runs on the current NVDA event thread; it only keeps
		# the control usable if the scheduler is temporarily unavailable.
		message(text)


def is_unigram_app_module(appModule):
	if not appModule:
		return False
	values = (
		getattr(appModule, "productName", ""),
		getattr(appModule, "appName", ""),
		getattr(appModule, "appPath", ""),
	)
	return any("unigram" in _normalized_text(value) for value in values)


def _parse_search_result_counter(obj):
	"""Return ``(current, total)`` for Unigram's search counter UIA object."""
	try:
		text = obj.name or obj.value or ""
	except Exception:
		return None
	match = _SEARCH_RESULT_COUNTER_RE.fullmatch(str(text))
	if not match:
		return None
	return tuple(map(int, match.groups()))


def _load_telegram_desktop_fallback_class():
	# Security note: this executes telegram.py from the user's own NVDA-managed
	# add-on directories (same trust level as any installed add-on). Candidate
	# paths must never be extended to network shares or world-writable locations.
	global _telegramDesktopFallbackClass, _telegramDesktopFallbackLoadAttempted
	if _telegramDesktopFallbackLoadAttempted:
		return _telegramDesktopFallbackClass
	_telegramDesktopFallbackLoadAttempted = True
	current_module = os.path.abspath(__file__)
	candidates = []
	try:
		for addon in addonHandler.getRunningAddons():
			try: addon_name = addon.manifest.get("name", "")
			except Exception: addon_name = ""
			if addon_name != "telegramDesktop":
				continue
			for attr in ("path", "_path"):
				addon_path = getattr(addon, attr, "")
				if addon_path:
					candidates.append(os.path.join(addon_path, "appModules", "telegram.py"))
	except Exception:
		pass
	try:
		import globalVars
		candidates.append(os.path.join(globalVars.appArgs.configPath, "addons", "telegramDesktop", "appModules", "telegram.py"))
	except Exception:
		pass
	for candidate in candidates:
		try:
			candidate = os.path.abspath(candidate)
			if candidate == current_module or not os.path.isfile(candidate):
				continue
			spec = importlib.util.spec_from_file_location("_unigramPlusTelegramDesktopFallback", candidate)
			if not spec or not spec.loader:
				continue
			module = importlib.util.module_from_spec(spec)
			spec.loader.exec_module(module)
			_telegramDesktopFallbackClass = getattr(module, "AppModule", None)
			if _telegramDesktopFallbackClass:
				return _telegramDesktopFallbackClass
		except Exception as e:
			try: log.debug("Could not load Telegram Desktop fallback app module from %r: %r" % (candidate, e))
			except Exception: pass
	return None


class File_transfer_progress_tracking:
	# Unigram 12.7 exposes file transfer progress on FileButton's UIA Value
	# pattern while the control type is Button, not ProgressBar. Handle value
	# changes directly and poll only a directly focused transfer control when
	# Unigram does not raise a fresh event. Never search the focused message tree
	# from this recurring callback: some XAML controls block for seconds while
	# exposing their parent or children. Poll on NVDA's main event loop: using
	# threading.Timer here creates a fresh native thread for every sample.
	active = False
	interval = .35
	app = None
	_timer = None
	_scheduled = False
	_generation = 0
	_step = 10
	_last_value = {}  # key -> (percentage, fresh_val_str)
	_last_logged_id = None
	_candidate_automation_ids = ("Button", "Download", "Overlay")
	_candidate_roles = (Role.LINK, Role.BUTTON)

	@classmethod
	def _read_fresh_value(cls, obj):
		# Force a fresh value lookup. NVDAObjects.UIA caches Value property and
		# only invalidates it when the focused element raises ValueProperty changes.
		# Unigram's FileButton does not always raise those events, so we ask UIA
		# for the current value directly to avoid getting a stale percentage.
		try:
			import UIAHandler  # local import: UIAHandler may be unavailable at module load time
			elem = getattr(obj, "UIAElement", None)
			if elem is not None:
				try:
					v = elem.GetCurrentPropertyValueEx(UIAHandler.UIA.UIA_ValueValuePropertyId, True)
					if v is not None: return str(v)
				except Exception: pass
		except Exception: pass
		try: return obj.value or ""
		except Exception: return ""

	@classmethod
	def _parse_percentage(cls, val):
		if val is None: return None
		text = str(val).strip().replace("\0", "")
		if not text: return None
		match = re.search(r"[-+]?\d+(?:[\.,]\d+)?", text)
		if not match: return None
		try: percentage = int(float(match.group(0).replace(",", ".")))
		except (TypeError, ValueError): return None
		if percentage < 0 or percentage > 100: return None
		return percentage

	@classmethod
	def _get_automation_id(cls, obj):
		try: return getattr(obj, "UIAAutomationId", "") or ""
		except Exception: return ""

	@classmethod
	def _is_transfer_button(cls, obj):
		try: role = obj.role
		except Exception: return False
		return (
			role in cls._candidate_roles
			and cls._get_automation_id(obj) in cls._candidate_automation_ids
			and cls._is_inside_messages(obj)
		)

	@classmethod
	def _is_inside_messages(cls, obj):
		root = obj
		for _ in range(10):
			if not root:
				return False
			if cls._get_automation_id(root) == "Messages":
				return True
			try: parent = root.parent
			except Exception: return False
			if not parent or parent is root:
				return False
			root = parent

	@classmethod
	def _is_unigram_object(cls, obj):
		try: return is_unigram_app_module(getattr(obj, "appModule", None))
		except Exception: return False

	@classmethod
	def _is_visible(cls, obj):
		try:
			location = obj.location
			return bool(location and location.width and location.height)
		except Exception:
			return True

	@classmethod
	def _is_in_foreground(cls, obj):
		try:
			if not obj or not obj.isInForeground:
				return False
		except Exception:
			try:
				foreground = api.getForegroundObject()
				return bool(
					foreground
					and getattr(foreground, "windowHandle", None)
					and getattr(foreground, "windowHandle", None) == getattr(obj, "windowHandle", None)
				)
			except Exception:
				return False
		return True

	@classmethod
	def _get_key(cls, obj):
		aid = cls._get_automation_id(obj)
		elem = getattr(obj, "UIAElement", None)
		if elem is not None:
			try: return ("runtime", tuple(elem.GetRuntimeId()), aid)
			except Exception: pass
		try:
			location = obj.location
			if location:
				return ("location", getattr(obj, "windowHandle", 0), aid, location.left, location.top, location.width, location.height)
		except Exception: pass
		return ("object", getattr(obj, "windowHandle", 0), aid, id(obj))

	@classmethod
	def _format_percentage(cls, percentage):
		return _("%d percent") % percentage

	@classmethod
	def _get_step(cls):
		try: step = int(conf.get("fileTransferProgressInterval"))
		except (TypeError, ValueError): step = cls._step
		return max(1, min(100, step))

	@classmethod
	def handle_progress(cls, obj, speak_first=False):
		if conf.get("voicingPerformanceIndicators") == "none": return False
		if not cls._is_unigram_object(obj): return False
		if not cls._is_in_foreground(obj): return False
		if not cls._is_transfer_button(obj): return False
		val = cls._read_fresh_value(obj)
		percentage = cls._parse_percentage(val)
		if percentage is None: return False
		key = cls._get_key(obj)
		prev = cls._last_value.get(key)
		last_pct = prev[0] if prev else None
		should_speak = False
		if last_pct is None:
			should_speak = speak_first and percentage > 0
		elif percentage != last_pct:
			if percentage == 100 or last_pct == 0 or abs(percentage - last_pct) >= cls._get_step():
				should_speak = True
		cls._last_value[key] = (percentage, val)
		if len(cls._last_value) > 128:
			cls._last_value.pop(next(iter(cls._last_value)), None)
		if should_speak:
			try: log.info("File_transfer_progress_tracking: announcing %d%%" % percentage)
			except: pass
			queueHandler.queueFunction(queueHandler.eventQueue, speech.speakMessage, cls._format_percentage(percentage))
		if percentage == 100:
			# A completed transfer is terminal for this polling session. A future
			# transfer starts a new session from its value-change or focus event.
			cls.stop()
		return True

	@classmethod
	def tick(cls):
		if not cls.active: return
		try:
			obj = api.getFocusObject()
			if obj is None: return
			if not cls._is_unigram_object(obj):
				cls._last_logged_id = None
				return
			if not cls._is_in_foreground(obj):
				cls._last_logged_id = None
				return
			if conf.get("voicingPerformanceIndicators") == "none": return
			# The old fallback searched every descendant of the focused message on
			# every tick. Reply-markup and rich-message XAML providers can take
			# several seconds to answer those tree requests. A transfer control is
			# focusable, so polling the focus itself preserves the user-facing path
			# without touching unrelated UIA objects.
			if not cls._is_transfer_button(obj) or not cls._is_visible(obj): return
			# Log once per focused object so we can verify detection without spam.
			obj_id = id(obj)
			if cls._last_logged_id != obj_id:
				cls._last_logged_id = obj_id
				try:
					log.info(
						"File_transfer_progress_tracking: tracking aid=%r role=%r value=%r"
						% (cls._get_automation_id(obj), obj.role, cls._read_fresh_value(obj))
					)
				except: pass
			cls.handle_progress(obj, speak_first=True)
		except Exception as e:
			try: log.debug("File_transfer_progress_tracking error: %r" % e)
			except: pass
		finally:
			cls._schedule_next()

	@classmethod
	def _scheduled_tick(cls, generation):
		if generation != cls._generation:
			return
		cls._scheduled = False
		cls._timer = None
		cls.tick()

	@classmethod
	def _schedule_next(cls):
		if not cls.active or cls._scheduled:
			return
		try:
			import core
			generation = cls._generation
			cls._scheduled = True
			cls._timer = core.callLater(
				round(cls.interval * 1000),
				lambda: cls._scheduled_tick(generation),
			)
		except Exception as e:
			cls._scheduled = False
			cls._timer = None
			cls.active = False
			try: log.debug("Could not schedule file-transfer progress tracking: %r" % e)
			except Exception: pass

	@classmethod
	def start(cls):
		if cls.active: return
		cls._generation += 1
		cls.active = True
		cls._last_value = {}
		cls._last_logged_id = None
		try: log.info("File_transfer_progress_tracking started (mode=%s)" % conf.get("voicingPerformanceIndicators"))
		except Exception: pass
		cls._schedule_next()

	@classmethod
	def stop(cls):
		cls.active = False
		cls._generation += 1
		timer = cls._timer
		cls._timer = None
		cls._scheduled = False
		if timer is not None:
			try: timer.Stop()
			except Exception: pass
		cls._last_value = {}
		cls._last_logged_id = None


class File_transfer_progress_button:
	def event_valueChange(self):
		if conf.get("voicingPerformanceIndicators") == "none":
			return
		percentage = File_transfer_progress_tracking._parse_percentage(
			File_transfer_progress_tracking._read_fresh_value(self)
		)
		if percentage is not None and percentage < 100 and not File_transfer_progress_tracking.active:
			File_transfer_progress_tracking.start()
		if File_transfer_progress_tracking.handle_progress(self, speak_first=True):
			return
		return super().event_valueChange()



class Audio_and_video_button:
	def script_enter(self, gesture):
		# Capture the toggle state before activating, so we can announce the state the button
		# flips to (the app updates its own toggle state asynchronously after the click).
		toggled_on = State.PRESSED in self.states or State.CHECKED in self.states
		gesture.send()
		if self.UIAAutomationId == "Mute": new_name = _("Microphone on") if toggled_on else _("Microphone muted")
		elif self.UIAAutomationId == "Camera": new_name = _("Camera off") if toggled_on else _("Camera on")
		elif self.UIAAutomationId == "Audio": new_name = self.next.name if self.next else self.name
		elif self.UIAAutomationId == "Video": new_name = _("Camera on") if self.firstChild.name == "\ue964" else _("Camera off") if self.firstChild.name == "\ue963" else self.name
		_announce_call_state_later(new_name, 100)
	
	def initOverlayClass(self):
		self.bindGesture("kb:Enter", "enter")
		# self.bindGesture("kb:space", "enter")


class Message_list_item(ListItem):
	selected_media = -1
	media = None
	list_media = []
	UIAAutomationId = "Message_item"
	scriptCategory = "UnigramPlus"
	last_part_in_message = None
	index_last_part_in_message = 0

	@script(description=_("Announce the original message, the message that was replied to"), gesture="kb:leftArrow")
	def script_voice_answer(self, gesture):
		if self.selected_media > 0:
			self.script_next_media(gesture, True)
			return
		answer = next((item for item in self.children if item.UIAAutomationId == "Reply"), None)
		if answer and answer.name == "":
			answer = answer.firstChild
		if scriptHandler.getLastScriptRepeatCount() == 0 and answer: message(answer.name)
		elif scriptHandler.getLastScriptRepeatCount() == 1 and answer: answer.doAction()

	@script(description=_("Show message text in popup window"), gesture="kb:ALT+C")
	def script_show_text_message(self, gesture):
		rich_message = find_rich_message_root(self)
		message_text = extract_message_text(self)
		rich_text = extract_rich_message_text(rich_message, textInfos.POSITION_ALL) if rich_message else ""
		title = _("Rich message") if rich_message else _("message text")
		text = merge_message_text_and_rich_text(message_text, rich_text)
		if not text:
			message(_("This message does not contain text"))
			return
		TextWindow(text, title, readOnly=False)

	@script(description=_("Open comments"), gesture="kb:control+ALT+C")
	def script_openComentars(self, gesture):
		targetButton = next((item for item in reversed(self.children) if item.role == Role.LINK and item.UIAAutomationId == "Thread"), False)
		if targetButton:
			# self.isSkipName = 1
			targetButton.doAction()
		else: message(_("Button to open comments not found"))

	@script(description=_("Edit message"), gesture="kb:backspace")
	def script_edit_message(self, gesture):
		self.appModule.activate_option_for_menu((icons_from_context_menu["edit"]), "Messages")
	
	@script(description=_("Reply to message"), gesture="kb:enter")
	def script_reply_to_message(self, gesture):
		self.appModule.activate_option_for_menu((icons_from_context_menu["reply"]), "Messages")

	def script_next_message(self, gesture):
		# Deliver Down immediately. UIA tree walks here can stall the NVDA main
		# thread while Unigram updates its virtualized history.
		move_focus_to_text = conf.get("action_when_pressing_up_arrow_in_text_field") == "to_messages"
		app = self.appModule
		gesture.send()
		if conf.get("play_end_of_chat_sound") or move_focus_to_text:
			# The callback is tied to this source object; moving to another message
			# makes the source/focus comparison fail before endpoint work begins.
			app._schedule_end_of_chat_confirmation(self, move_focus_to_text)

	def script_next_media(self, gesture, revers=False):
		self.list_media = self.list_media or [item for item in self.children if item.role == Role.LISTITEM]
		obj = None
		if revers:
			self.selected_media -= 1
			obj = self.list_media[self.selected_media]
		elif self.selected_media < len(self.list_media)-1:
			self.selected_media += 1
			obj = self.list_media[self.selected_media]
		if not obj: return
		self.media = obj
		if obj.firstChild.UIAAutomationId == "Subtitle": name = _("Photo")
		elif obj.firstChild.UIAAutomationId == "Texture": name = _("Video")
		else:
			name = next((item.name for item in obj.children if item.UIAAutomationId in ("Title",)) , "Медіа")
		message(name)
		api.setNavigatorObject(obj.simpleFirstChild)

	@script(description=_("Announces the time a message was sent or received, as well as a list of reactions. Double-clicking toggles the announcement mode for this information."), gesture="kb:ALT+W")
	def script_toggle_sounding_message_information(self, gesture):
		if scriptHandler.getLastScriptRepeatCount() == 0:
			message(self.last_part_in_message)
		elif scriptHandler.getLastScriptRepeatCount() == 1:
			conf.set("announce_endthe_message", not conf.get("announce_endthe_message"))
			if conf.get("announce_endthe_message"): message(_("The display of message sending or receiving time and the list of installed emojis is enabled."))
			else: message(_("The display of message sending or receiving time and the list of installed emojis is  disabled."))

	def initOverlayClass(self):
		try:
			self.positionInfo = self.parent.positionInfo
		except Exception:
			# A recycled service-message container can briefly lack its parent.
			pass
		self.states.discard(State.SELECTABLE)
		keywords = keywordsInMessages.get(conf.get("lang"), keywordsInMessages["en"])
		self.keywords = keywords
		positions = [self.name.find(marker) for marker in keywords[2:4]]
		positions = [position for position in positions if position >= 0]
		if positions:
			index = min(positions)
			self.index_last_part_in_message = index
			self.last_part_in_message = self.name[index:]
		else:
			# The Unigram display language can differ from the add-on language.
			# Avoid the legacy [-1:] slice when no localized status marker matches.
			self.index_last_part_in_message = 0
			self.last_part_in_message = ""
		
		# Bind once per overlay rather than only when it is created with the
		# setting enabled. This makes a settings change effective immediately for
		# an already-realized final message.
		self.bindGesture("kb:downArrow", "next_message")

	__gestures = {
		"kb:ALT+C": "show_text_message",
		"kb:rightArrow": "next_media",
		"kb:leftArrow": "voice_answer",
		"kb:backspace": "edit_message",
		"kb:enter": "reply_to_message",
		# "kb:control+leftArrow": "previous_reaction",
		# "kb:control+rightArrow": "next_reaction",
		# "kb:control+enter": "activate_reaction",
	}


class SettingsPanelListItem:

	def script_activate_element(self, gesture):
		self.firstChild.doAction()
		self.appModule.script_toLastMessage(gesture)

	__gestures = {
		"kb:enter": "activate_element",
		"kb:space": "activate_element",
	}


class ExplanationCorrectAnswerInQuiz:
	def script_activate_element(self, gesture):
		gesture.send()
		elements = self.appModule.getElements()
		try: obj = elements[1].firstChild.firstChild.firstChild
		except: obj = None
		if not obj: return False
		# message(obj.name)
		TextWindow(obj.name, _("Explanation"), readOnly=False)

	__gestures = {
		"kb:enter": "activate_element",
		"kb:space": "activate_element",
	}


class Saved_items:
	# store frequently used window elements in cache for faster access
	_items = {}
	def get(self, key):
		id = api.getFocusObject().windowHandle
		try: return self._items[id][key]
		except: return False
	def save(self, key, obj):
		# id = obj.windowHandle
		id = api.getFocusObject().windowHandle
		if id not in self._items: self._items[id] = {}
		self._items[id][key] = obj


class _MainLoopPoller:
	"""Schedule UIA polling on NVDA's event loop, never a native Timer thread."""
	_timer = None
	_scheduled = False
	_generation = 0

	@classmethod
	def _scheduled_poll(cls, generation):
		if generation != cls._generation:
			return
		cls._scheduled = False
		cls._timer = None
		cls.tick()

	@classmethod
	def _schedule_poll(cls):
		if not cls.active or cls.pouse or cls._scheduled:
			return
		try:
			import core
			generation = cls._generation
			cls._scheduled = True
			cls._timer = core.callLater(
				round(cls.interval * 1000),
				lambda: cls._scheduled_poll(generation),
			)
		except Exception as error:
			cls._scheduled = False
			cls._timer = None
			try: log.debug("Could not schedule %s polling: %r" % (cls.__name__, error))
			except Exception: pass

	@classmethod
	def _cancel_poll(cls):
		cls._generation += 1
		timer = cls._timer
		cls._timer = None
		cls._scheduled = False
		if timer is not None:
			try: timer.Stop()
			except Exception: pass

	@classmethod
	def _restart_poll(cls):
		cls._cancel_poll()
		cls._schedule_poll()


class Title_change_tracking(_MainLoopPoller):
	active = False
	pouse = False
	interval = .5
	saved_items = False
	@classmethod
	def tick(cls):
		if not cls.active or cls.pouse: return
		try:
			title = cls.saved_items.get("profile name")
			if not title or not title.isInForeground:
				cls.pouse = True
				return False
			last_profile_name = cls.saved_items.get("last profile name") or ("",)
			if title.childCount > 1 and title.lastChild.name != last_profile_name[-1]:
				if title.firstChild.name == last_profile_name[0]:
					# Announce changes only if these changes are not related to switching to another chat
					text = title.lastChild.name
					queueHandler.queueFunction(queueHandler.eventQueue, message, text)
				new_title = [item.name for item in title.children]
				cls.saved_items.save("last profile name", new_title)
		except Exception as error:
			try: log.debug("Could not track chat-title changes: %r" % error)
			except Exception: pass
		finally:
			cls._schedule_poll()
	@classmethod
	def toggle(cls, saved_items=False):
		if not conf.get("automatically announce activity in chats") or not saved_items:
			cls.saved_items = saved_items
			cls.active = True
			cls.pouse = False
			conf.set("automatically announce activity in chats", True)
			cls._restart_poll()
			return True
		else:
			cls.active = False
			cls._cancel_poll()
			conf.set("automatically announce activity in chats", False)
			return False
	@classmethod
	def restore(cls, saved_items=False):
		cls.pouse = False
		cls.active = True
		cls.saved_items = saved_items
		cls.saved_items.save("last profile name", None)
		cls._restart_poll()


class Typing_sound_tracking(_MainLoopPoller):
	# Polls the chat-title status and loops Typing.wav while the other side is typing/recording/etc.
	active = False
	pouse = False
	interval = .3
	saved_items = False
	is_playing = False
	@classmethod
	def _is_typing(cls, status_text):
		if not status_text: return False
		text = status_text.lower()
		for kw in typing_keywords:
			if kw.lower() in text: return True
		return False
	@classmethod
	def start_sound(cls):
		if cls.is_playing: return
		cls.is_playing = True
		try: winsound.PlaySound(baseDir+"Typing.wav", winsound.SND_ASYNC | winsound.SND_LOOP)
		except: cls.is_playing = False
	@classmethod
	def stop_sound(cls):
		if not cls.is_playing: return
		cls.is_playing = False
		try: winsound.PlaySound(None, 0)
		except: pass
	@classmethod
	def _chat_status(cls):
		# Returns the live status text from the chat title, or None when no chat is
		# really in the foreground (app closed / left the chat) so the caller can pause.
		title = cls.saved_items.get("profile name") if cls.saved_items else None
		if not title: return None
		try:
			if not title.isInForeground: return None
		except Exception:
			return None
		try:
			location = title.location
			if not location or not location.width: return None
		except Exception:
			return None
		try:
			return title.lastChild.name if title.childCount > 1 else ""
		except Exception:
			return ""
	@classmethod
	def tick(cls):
		if not cls.active or cls.pouse:
			cls.stop_sound()
			return
		try:
			status_text = cls._chat_status()
			if status_text is None:
				# No chat is really in the foreground anymore: stop and wait for focus.
				cls.stop_sound()
				cls.pouse = True
				return
			# Reconcile the looping sound with the live status on every tick.
			if cls._is_typing(status_text): cls.start_sound()
			else: cls.stop_sound()
		except Exception:
			cls.stop_sound()
		finally:
			cls._schedule_poll()
	@classmethod
	def toggle(cls, saved_items=False):
		if not conf.get("play_typing_sound") or not saved_items:
			cls.saved_items = saved_items
			cls.active = True
			cls.pouse = False
			conf.set("play_typing_sound", True)
			cls._restart_poll()
			return True
		else:
			cls.active = False
			cls._cancel_poll()
			cls.stop_sound()
			conf.set("play_typing_sound", False)
			return False
	@classmethod
	def restore(cls, saved_items=False):
		cls.pouse = False
		cls.active = True
		cls.saved_items = saved_items
		cls._restart_poll()


class Chat_update(_MainLoopPoller):
	active = False
	pouse = False
	interval = .3
	app = False
	@classmethod
	def tick(cls):
		if not cls.active or cls.pouse: return
		try:
			try : last_message = cls.app.getMessagesElement().lastChild
			except: last_message = False
			if not last_message or not last_message.isInForeground:
				cls.pouse = True
				return False
			# The first item is the name of the chat in which the last message was recorded
			# The second item is the message index
			last_saved_message = cls.app.saved_items.get("last message") or ("", "")
			# If there is a problem getting the message index, terminate the function and call the next iteration
			try:
				last_message.positionInfo["indexInGroup"]
				last_message.positionInfo["similarItemsInGroup"]
			except:
				return
			if last_message.positionInfo["indexInGroup"] != last_saved_message[1] and last_message.positionInfo["indexInGroup"] == last_message.positionInfo["similarItemsInGroup"]:
				try:
					title = cls.app.saved_items.get("profile name").firstChild.name
				except:
					title = False
				keywords = keywordsInMessages.get(conf.get("lang"), keywordsInMessages["en"])
				if ((title == last_saved_message[0]) or not title) and keywords[3] in last_message.name[-60:]:
					text = cls.app.action_message_focus(last_message.firstChild)
					queueHandler.queueFunction(queueHandler.eventQueue, message, text)
				try:
					new_message = (title, last_message.positionInfo["indexInGroup"])
					cls.app.saved_items.save("last message", new_message)
				except: pass
		except Exception as error:
			try: log.debug("Could not track new chat messages: %r" % error)
			except Exception: pass
		finally:
			cls._schedule_poll()
	@classmethod
	def toggle(cls, app=False):
		if not conf.get("automatically announce new messages") or not app:
			cls.active = True
			cls.pouse = False
			conf.set("automatically announce new messages", True)
			cls.app = app
			cls._restart_poll()
			return True
		else:
			cls.active = False
			cls._cancel_poll()
			conf.set("automatically announce new messages", False)
			return False
	@classmethod
	def restore(cls, app=False):
		cls.pouse = False
		cls.active = True
		cls.app = app
		cls.app.saved_items.save("last message", None)
		cls._restart_poll()


class EditableText(editableText.EditableText):

	def script_caret_moveByLine(self, gesture):
		if gesture.mainKeyName != "upArrow":
			return super().script_caret_moveByLine(gesture)
		info = None
		try:
			info = self.makeTextInfo(textInfos.POSITION_ALL)
		except Exception:
			pass
		if info and info.text == "":
			if conf.get("action_when_pressing_up_arrow_in_text_field") == "to_messages":
				self.appModule.script_toLastMessage(None)
			elif conf.get("action_when_pressing_up_arrow_in_text_field") == "to_last_focused_message":
				self.appModule.script_toLastFocusedMessage(None)
			else: message("")
			return
		return super().script_caret_moveByLine(gesture)


class ChatListItem(ListItem):
	# Current Unigram uses EB00 for a chat mention. E986 is retained for older
	# ChatCell templates whose default XAML glyph is still exposed through UIA.
	_MENTION_GLYPHS = {"\ueb00", "\ue986"}
	_MAX_BADGE_SEARCH_DEPTH = 6

	@classmethod
	def _has_unread_mentions(cls, obj):
		queue = [(obj, 0)]
		seen = set()
		while queue:
			node, depth = queue.pop(0)
			node_id = id(node)
			if node_id in seen:
				continue
			seen.add(node_id)
			try: automation_id = node.UIAAutomationId
			except Exception: automation_id = ""
			if automation_id == "UnreadMentionsLabel":
				try: glyph = (node.name or node.value or "").strip()
				except Exception: glyph = ""
				if glyph in cls._MENTION_GLYPHS:
					return True
			if depth >= cls._MAX_BADGE_SEARCH_DEPTH:
				continue
			try: children = node.children
			except Exception: children = ()
			for child in children:
				queue.append((child, depth + 1))
		return False

	def _move_to_chat_with_unread_mentions(self, forward):
		try: candidate = self.next if forward else self.previous
		except Exception: candidate = None
		visited = set()
		while candidate and id(candidate) not in visited:
			visited.add(id(candidate))
			if self._has_unread_mentions(candidate):
				candidate.setFocus()
				return True
			try: candidate = candidate.next if forward else candidate.previous
			except Exception: candidate = None
		message(_("No more chats with unread mentions in this direction"))
		return False

	# Translators: Input gesture description for Ctrl+Alt+Up/Down in the chat list.
	@script(
		description=_("Move to the next or previous chat with unread mentions"),
		gestures=["kb:control+alt+downArrow", "kb:control+alt+upArrow"],
	)
	def script_moveToChatWithUnreadMentions(self, gesture):
		try: identifier = gesture.identifiers[0].casefold()
		except Exception: identifier = ""
		self._move_to_chat_with_unread_mentions("downarrow" in identifier)


class AppModule(appModuleHandler.AppModule):
	
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.isUnigramWindow = is_unigram_app_module(self)
		self._voiceRecordingState = VoiceRecordingState()
		self._voiceRecordingOutcome = VoiceRecordingOutcome(_VOICE_RECORDING_OUTCOME_POLL_LIMIT)
		self._voiceRecordingMonitorRunning = False
		self._voiceRecordingButton = None
		self._voiceRecordingDiscoveryFocus = None
		self._autoFocusChatListDone = False
		self._autoFocusChatListScheduled = False
		self._autoFocusChatListAttempts = 0
		self._autoFocusChatListGeneration = 0
		self._endOfChatProbeGeneration = 0
		self._messagesButton = None
		self._mainWindowHandle = None
		self._callWindowHandles = set()
		if not self.isUnigramWindow:
			self._fallbackAppModule = None
			fallbackClass = _load_telegram_desktop_fallback_class()
			if fallbackClass:
				try:
					self._fallbackAppModule = fallbackClass(*args, **kwargs)
				except Exception as e:
					try: log.debug("Could not initialize Telegram Desktop fallback app module: %r" % e)
					except Exception: pass
			return
		self.saved_items = Saved_items()
		if conf.get("automatically announce new messages") and not Chat_update.active: Chat_update.restore(self)
		if conf.get("automatically announce activity in chats") and not Title_change_tracking.active: Title_change_tracking.restore(self.saved_items)
		if conf.get("play_typing_sound") and not Typing_sound_tracking.active: Typing_sound_tracking.restore(self.saved_items)
		if (
			conf.get("voicingPerformanceIndicators") != "none"
			and not File_transfer_progress_tracking.active
		):
			File_transfer_progress_tracking.start()
		self.app_version = self.productVersion
		# assign hotkeys for the function of reading messages by numbering
		for i in range(10): self.bindGesture("kb:NVDA+control+%d" % i, "reviewRecentMessage")
		# assign hotkeys for the function rewind voice messages
		# for i in range(10): self.bindGesture("kb:control+ALT+%d" % i, "rewind_voice_message")
		# Binding reactions to the corresponding hotkeys
		# for i in range(1,8): self.bindGesture("kb:NVDA+ALT+%d" % i, "set_reaction")
		self._voiceRecordingMonitorRunning = True
		self._scheduleVoiceRecordingPoll()

	def terminate(self):
		self._voiceRecordingMonitorRunning = False
		self._autoFocusChatListGeneration += 1
		self._autoFocusChatListScheduled = False
		self._endOfChatProbeGeneration = getattr(self, "_endOfChatProbeGeneration", 0) + 1
		if getattr(self, "isUnigramWindow", False):
			File_transfer_progress_tracking.stop()
		super().terminate()

	def event_appModule_gainFocus(self):
		if not getattr(self, "isUnigramWindow", False):
			return
		self._autoFocusChatListAttempts = 0
		self._scheduleAutoFocusChatList()

	def _scheduleAutoFocusChatList(self):
		if (
			self._autoFocusChatListDone
			or self._autoFocusChatListScheduled
			or not conf.get("autoFocusChatList")
		):
			return
		try:
			import core
			generation = self._autoFocusChatListGeneration
			self._autoFocusChatListScheduled = True
			core.callLater(
				_AUTO_FOCUS_CHAT_LIST_DELAY_MS,
				self._autoFocusChatListTick,
				generation,
			)
		except Exception as e:
			self._autoFocusChatListScheduled = False
			try: log.debug("Could not schedule automatic chat-list focus: %r" % e)
			except Exception: pass

	def _autoFocusChatListTick(self, generation):
		if generation != self._autoFocusChatListGeneration:
			return
		self._autoFocusChatListScheduled = False
		if self._autoFocusChatListDone or not conf.get("autoFocusChatList"):
			return
		try:
			focus = api.getFocusObject()
			focus_is_ready = (
				focus is not None
				and getattr(focus, "appModule", None) is self
				and focus.isInForeground
			)
			if not focus_is_ready:
				focus = None
			surface = None
			if focus is not None:
				surface = self._classify_window_surface(focus)
			# VoIP pages are separate WindowEx instances and expose ActiveButtons or
			# BottomRoot close to their focusable controls. Unknown handles must remain
			# retryable: XAML often raises startup focus before ChatsList materializes,
			# and Unigram also supports multiple chat windows with different handles.
			if surface == "call":
				self._autoFocusChatListDone = True
				return
			if focus is not None and (
				focus.role == Role.LISTITEM
				and getattr(getattr(focus, "parent", None), "UIAAutomationId", "") == "ChatsList"
			):
				self._autoFocusChatListDone = True
				return
			if focus is not None:
				# Mark first to prevent the focus event raised by setFocus() from
				# scheduling a duplicate callback. Restore it if the list is not ready.
				self._autoFocusChatListDone = True
				if self.script_toChatList(None, arg=True):
					return
				self._autoFocusChatListDone = False
		except Exception as e:
			self._autoFocusChatListDone = False
			try: log.debug("Could not focus the chat list automatically: %r" % e)
			except Exception: pass
		self._autoFocusChatListAttempts += 1
		if self._autoFocusChatListAttempts < _AUTO_FOCUS_CHAT_LIST_RETRY_LIMIT:
			self._scheduleAutoFocusChatList()

	def getScript(self, gesture):
		if not getattr(self, "isUnigramWindow", False):
			fallback = getattr(self, "_fallbackAppModule", None)
			if fallback:
				try: return fallback.getScript(gesture)
				except Exception: return None
			return None
		return super().getScript(gesture)

	def _classify_window_surface(self, obj):
		"""Return ``main``, ``call``, or ``None`` from a nearby stable UIA marker."""
		try:
			handle = obj.windowHandle
		except Exception:
			return None
		if not handle:
			return None
		try:
			automation_id = getattr(obj, "UIAAutomationId", "")
		except Exception:
			automation_id = ""
		call_handles = getattr(self, "_callWindowHandles", set())
		# Direct markers are authoritative if Windows reused a recently closed
		# WindowEx handle for a different Unigram surface.
		if automation_id in _MAIN_WINDOW_AUTOMATION_IDS:
			call_handles.discard(handle)
			self._callWindowHandles = call_handles
			self._mainWindowHandle = handle
			return "main"
		if automation_id in _CALL_WINDOW_AUTOMATION_IDS:
			call_handles.add(handle)
			self._callWindowHandles = call_handles
			if self._mainWindowHandle == handle:
				self._mainWindowHandle = None
			return "call"
		# This method is reached by every focus event. Once identified, comparing
		# NVDA's cached native handle avoids repeated synchronous UIA parent calls.
		if handle == self._mainWindowHandle:
			return "main"
		if handle in call_handles:
			return "call"
		marker = _find_ancestor_by_automation_id(obj, _WINDOW_SURFACE_AUTOMATION_IDS, max_depth=5)
		if not marker:
			return None
		try:
			marker_id = getattr(marker, "UIAAutomationId", "")
		except Exception:
			return None
		if marker_id in _CALL_WINDOW_AUTOMATION_IDS:
			call_handles.add(handle)
			self._callWindowHandles = call_handles
			if self._mainWindowHandle == handle:
				self._mainWindowHandle = None
			return "call"
		call_handles.discard(handle)
		self._callWindowHandles = call_handles
		self._mainWindowHandle = handle
		return "main"

	def _is_main_window_object(self, obj):
		try:
			return bool(self._mainWindowHandle and obj.windowHandle == self._mainWindowHandle)
		except Exception:
			return False

	scriptCategory = "UnigramPlus"
	profile_panel_element = False
	isDelete = False
	isOpenProfile = False
	isSkipName = 0
	isRecord = False
	execute_context_menu_option = False
	is_exit_from_media = False
	keys = {
		"upArrow": KeyboardInputGesture.fromName("upArrow"),
		"downArrow": KeyboardInputGesture.fromName("downArrow"),
		"fixed_downArrow": KeyboardInputGesture.fromName("shift+downArrow"),
		"Applications": KeyboardInputGesture.fromName("Applications"),
		"delete": KeyboardInputGesture.fromName("delete"),
		"escape": KeyboardInputGesture.fromName("escape"),
		"space": KeyboardInputGesture.fromName("space"),
	}


	def getMessagesElement(self):
		obj = self.saved_items.get("messages")
		if not obj or not obj.location or not obj.location.width:
			# obj = next((item for item in self.getElements() if item.UIAAutomationId == "Messages"), False)
			obj = None
			item = self.get_first_item()
			while item:
				if item.UIAAutomationId == "Messages":
					obj = item
					item = None
				else: item = item.next
			if obj: self.saved_items.save("messages", obj)
		return obj

	def _get_last_focused_message(self):
		obj = self.saved_items.get("last focus object")
		try:
			if obj and self.is_message_object(obj) and obj.location and obj.location.width:
				return obj
		except Exception:
			pass
		return None

	def getChatsListElement(self):
		targetList = self.saved_items.get("chats")
		if targetList and targetList.location and targetList.location.width: return targetList
		if is_version_greater(self.productVersion, "11.2.13.0"):
			targetList = next((item for item in self.getElements() if item.role == Role.LIST and item.UIAAutomationId == "ChatsList"), False)
		else:
			targetList = next((item for item in reversed(self.getElements()) if item.role == Role.TABCONTROL and item.UIAAutomationId == "rpMasterTitlebar"), False)
			if not targetList: return False
			targetList = next((item for item in targetList.firstChild.children if item.role == Role.LIST and 	item.UIAAutomationId == "ChatsList"), False)
		if targetList: self.saved_items.save("chats", targetList)
		return targetList

	def parse_version(v):
		return list(map(int, v.split('.')))

	def getElements(self):
		try: return api.getForegroundObject().lastChild.previous.children
		except: return []
	
	def get_first_item(self):
		try: return api.getForegroundObject().lastChild.previous.firstChild
		except: return []


	def get_settings_panel(self):
		settings_panel = next((item for item in self.getElements() if item.role in (Role.PANE, Role.LIST) and item.UIAAutomationId in ("ScrollingHost", "List", "") and (item.previous.UIAAutomationId == "DetailHeaderPresenter"  or item.location.width > 320)), None)
		if not settings_panel: return False
		return next(( item for item in settings_panel.children if State.FOCUSABLE in item.states), settings_panel.firstChild)

	def get_contacts_list(self):
		try:
			message("11")
			dialog = next((item for item in self.getElements() if item.role == Role.DIALOG and item.firstChild.next.UIAAutomationId == "SearchField" and item.firstChild.next.next.role == Role.LIST and item.firstChild.next.next.UIAAutomationId == "ScrollingHost"), None)
			message("22")
			first_item = next((item for item in dialog.children if item.role == Role.LISTITEM), None)
			message("333")
			return first_item
		except Exception as e:
			print(e)
			return False

	def get_settings_list(self):
		a = next((item for item in self.getElements() if item.role == Role.PANE and item.UIAAutomationId == "ScrollingHost" and item.firstChild.next.UIAAutomationId == "Title" and item.firstChild.next.next.UIAAutomationId == "Identity"), None)
		if not a:
			return False
		try: b = a.firstChild.next.next.next.next.firstChild
		except: b = False
		if b: return b
		else: return False


	def is_message_object(self, obj):
		return _is_message_list_item(obj)

	def _same_uia_element(self, first, second):
		"""Compare UIA elements even when NVDA assigned different overlays."""
		if first is None or second is None:
			return False
		try:
			if first == second:
				return True
		except Exception:
			pass
		try:
			first_id = tuple(first.UIAElement.GetRuntimeId())
			second_id = tuple(second.UIAElement.GetRuntimeId())
			return bool(first_id) and first_id == second_id
		except Exception:
			return False

	def _get_current_message_row_and_list(self, obj):
		"""Return the current row and its Messages list using only parent links.

		Some Unigram message templates insert extra UIA wrappers between
		``Message_item`` and the list row. The cached Messages object is scoped to
		the window, not the open chat, so resolving upward from the source avoids
		both template variance and a stale list from the previously opened chat.
		"""
		candidate = obj
		for _ in range(12):
			if candidate is None:
				return None
			try:
				parent = candidate.parent
			except Exception:
				return None
			if parent is None or parent is candidate:
				return None
			try:
				if parent.UIAAutomationId == "Messages":
					return candidate, parent
			except Exception:
				pass
			candidate = parent
		return None

	def _remember_messages_button(self, obj):
		"""Cache MessagesButton when NVDA has already materialized it.

		Never discover this control by walking the foreground UIA tree from a
		keyboard handler. A stale XAML element can make ``child.next`` block the
		NVDA main thread for several seconds while Unigram updates its history.
		"""
		try:
			if getattr(obj, "UIAAutomationId", "") == "MessagesButton":
				self._messagesButton = obj
				return True
		except Exception:
			pass
		return False

	def _messages_button_visibility(self):
		"""Return cached MessagesButton visibility, or ``None`` when unavailable."""
		button = getattr(self, "_messagesButton", None)
		if not button:
			return None
		try:
			if not getattr(button, "isInForeground", True):
				self._messagesButton = None
				return None
			# A button is recreated when a chat view is rebuilt. Accessing its
			# runtime ID turns a disconnected cached UIA object into an explicit
			# unknown state without walking the new visual tree.
			button.UIAElement.GetRuntimeId()
			states = button.states
			location = button.location
			if State.OFFSCREEN in states:
				return False
			if not location or location.width <= 0 or location.height <= 0:
				return False
			return True
		except Exception:
			self._messagesButton = None
			return None

	def _get_end_of_chat_candidate(self, obj, messages=None):
		"""Return ``(messages, row)`` when the focused row is ``lastChild``.

		This matches RussianMod's working endpoint rule while using UIA runtime
		identity first. When Unigram temporarily breaks the message ancestry,
		fall back to RussianMod's message-text strategy rather than walking the
		foreground UIA tree.
		"""
		source = obj
		resolved = self._get_current_message_row_and_list(obj)
		if resolved is not None:
			row, messages = resolved
		else:
			if messages is None:
				try:
					messages = self.getMessagesElement()
				except Exception:
					return None
			try:
				row = obj.parent
			except Exception:
				return None
		if not messages or row is None:
			return None
		try:
			last_row = messages.lastChild
		except Exception:
			return None
		if not last_row:
			return None
		if not self._same_uia_element(row, last_row):
			# RussianMod compares these raw row names. Keep that fallback for
			# recycled XAML objects whose runtime ID changes at the endpoint.
			try:
				row_name = row.name
				last_row_name = last_row.name
				if not row_name or row_name != last_row_name:
					# Unigram occasionally exposes the focused Message_item outside its
					# real row (logs may even report positions such as "39 of 38"). In
					# that state RussianMod compares the message text with the realized
					# last row. Require a substantial exact/containment match to avoid
					# mistaking short, repeated service labels for the endpoint.
					source_name = _normalized_text(source.name)
					last_row_name = _normalized_text(last_row_name)
					if not source_name or not last_row_name:
						return None
					shorter, longer = sorted(
						(source_name, last_row_name),
						key=len,
					)
					if len(shorter) < 32 or (shorter != longer and shorter not in longer):
						return None
			except Exception:
				return None
		return messages, row

	def _get_end_of_chat_state(self, obj, messages=None):
		"""Return the RussianMod-compatible realized-last-message state."""
		return self._get_end_of_chat_candidate(obj, messages) is not None

	def _is_last_message_in_chat(self, obj):
		return self._get_end_of_chat_state(obj) is True

	def _schedule_end_of_chat_confirmation(
		self,
		source,
		move_focus_to_text=False,
	):
		"""Schedule a source-bound endpoint check without reading UIA immediately."""
		self._endOfChatProbeGeneration = getattr(self, "_endOfChatProbeGeneration", 0) + 1
		generation = self._endOfChatProbeGeneration
		try:
			import core
			core.callLater(
				_END_OF_CHAT_PROBE_DELAY_MS,
				self._confirm_end_of_chat,
				generation,
				source,
				move_focus_to_text,
			)
			return True
		except Exception:
			log.debug("Could not schedule end-of-chat confirmation", exc_info=True)
			return False

	def _confirm_end_of_chat(
		self,
		generation,
		source,
		move_focus_to_text=False,
	):
		if generation != getattr(self, "_endOfChatProbeGeneration", 0):
			return
		try:
			candidate = self._get_end_of_chat_candidate(source)
			if candidate is None:
				log.debug("End-of-chat probe did not match Messages.lastChild")
				return
		except Exception:
			log.debug("Could not confirm end-of-chat state", exc_info=True)
			return
		log.debug("End-of-chat probe matched Messages.lastChild")
		if conf.get("play_end_of_chat_sound"):
			play_end_of_chat_sound()
		if (
			move_focus_to_text
			and conf.get("action_when_pressing_up_arrow_in_text_field") == "to_messages"
		):
			self.script_moveFocusToTextMessage(None)

	# The function of changing the playback speed of a voice message
	@script(description=_("Increase/decrease the playback speed of voice messages"), gesture="kb:ALT+S")
	def script_voiceMessageAcceleration(self, gesture):
		targetButton = next((item for item in self.getElements() if item.role == Role.BUTTON and item.UIAAutomationId == "SpeedButton"), False)
		if not targetButton and self.getElements()[0].role == Role.WINDOW:
			targetButton = next((item for item in self.getElements()[0].children if item.role == Role.BUTTON and item.UIAAutomationId == "SpeedButton"), False)
		if targetButton: targetButton.doAction()
		else: message(_("Nothing is playing right now"))

	# Audio player close function
	@script(description=_("Close audio player"), gesture="kb:ALT+E")
	def script_closingVoiceMessage(self, gesture, isMessage = True):
		try: targetButton = next((item for item in self.getElements()[1:] if item.previous.role == Role.TOGGLEBUTTON and item.previous.UIAAutomationId == "ShuffleButton"), False)
		except: targetButton = False
		if targetButton:
			lastFocus = api.getFocusObject()
			targetButton.doAction()
			lastFocus.setFocus()
			message(_("The audio player has been closed"))
		else: message(_("Nothing is playing right now"))

	# Voice message pause function
	@script(description=_("Play/pause the voice message currently playing"), gesture="kb:ALT+P")
	def script_pauseVoiceMessage(self, gesture):
		targetButton = next((item for item in self.getElements() if item.role == Role.BUTTON and item.UIAAutomationId == "PlaybackButton"), False)
		if targetButton:
			lastFocus = api.getFocusObject()
			targetButton.doAction()
			lastFocus.setFocus()
		else: message(_("Nothing is playing right now"))

	# Playing and opening media with the space bar
	def script_actionMediaInMessage(self, gesture):
		obj = api.getFocusObject()
		message_states = obj.states
		gesture.send()
		if not self.is_message_object(obj): return
		def spechState():
			is_save_focus = True
			targetButton = None
			if obj.states != message_states: return
			if obj.media:
				targetButton = next((item for item in obj.media.children if item.role in (Role.LINK, Role.BUTTON) and item.UIAAutomationId == "Button"), None)
				if targetButton and targetButton.previous and targetButton.previous.UIAAutomationId != "Button": is_save_focus = False
			else:
				item = obj.firstChild
				while item:
					if item.role in (Role.LINK, Role.BUTTON) and item.UIAAutomationId == "Button":
						targetButton = item
						if item.location.width > 150: is_save_focus = False
						break
					# elif item.role == Role.CHECKBOX and item.simpleFirstChild.UIAAutomationId == "Button":
						targetButton = item.simpleFirstChild
						if targetButton.location.width > 150 or item.firstChild.UIAAutomationId != "Button": is_save_focus = False
						break
					item = item.next
			if not targetButton: return
			targetButton.doAction()
			if is_save_focus:
				obj.setFocus()
			else:
				self.is_exit_from_media = True
		thr = Timer(.1, spechState).start()

	# Go to chat list
	@script(description=_("Move focus to chat list"), gesture="kb:ALT+1")
	def script_toChatList(self, gesture, arg = False):
		obj = api.getFocusObject()
		lastFocusChatElement = self.saved_items.get("last focused chat")
		if lastFocusChatElement and lastFocusChatElement.location and lastFocusChatElement.location.width:
			if obj == lastFocusChatElement: message(obj.name)
			else: lastFocusChatElement.setFocus()
			return True
		try: targetList = self.getChatsListElement()
		except: targetList = None
		if not targetList:
			settings_list = self.get_settings_list()
			if settings_list:
				settings_list.setFocus()
				return True
			# contacts_list = self.get_contacts_list()
			# if contacts_list:
				# contacts_list.setFocus()
				# return True
			if not arg: message(_("Chat list not found"))
			return
		if targetList.firstChild:
			targetList = targetList.firstChild
			if targetList.role == Role.BUTTON and targetList.next: targetList =  targetList.next
			if targetList.role and targetList.role == Role.LISTITEM:
				targetList.setFocus()
				return True
		if not arg: message(_("Chat list is empty"))
		return False

	# Go to the last message in the chat
	@script(description=_("Move focus to the last message in an open chat"), gesture="kb:ALT+2")
	def script_toLastMessage(self, gesture):
		# A partially loaded long history can have a locally last realized row that
		# is not the chat's true endpoint. Prefer Unigram's own Go to bottom action.
		button = getattr(self, "_messagesButton", None)
		if button and self._messages_button_visibility() is True:
			try:
				button.doAction()
				return True
			except Exception:
				pass
		focusObj = api.getFocusObject()
		if self.is_message_object(focusObj):
			if self._is_last_message_in_chat(focusObj):
				play_end_of_chat_sound()
				message(focusObj.name)
			else:
				# When the bottom-arrow fade is still in progress, a candidate final
				# row can be temporarily inconclusive. Keep a source-bound probe while
				# End performs its normal navigation; it cancels if a newer row appears.
				self._schedule_end_of_chat_confirmation(focusObj)
				KeyboardInputGesture.fromName("end").send()
			return True
		obj = self.getMessagesElement()
		try:
			obj.lastChild.setFocus()
			KeyboardInputGesture.fromName("end").send()
		except:
			if obj and not obj.lastChild:
				message(_("This chat is empty"))
				return True
			branch_list = self.get_branch_list()
			if branch_list:
				branch_list.firstChild.setFocus()
				return
			profile_panel = self.get_profile_panel()
			if profile_panel:
				profile_panel.setFocus()
				return
			settings_panel = self.get_settings_panel()
			if settings_panel:
				settings_panel.setFocus()
				return
			message(_("No open chat"))

	def script_toLastFocusedMessage(self, gesture):
		obj = self._get_last_focused_message()
		if obj:
			obj.setFocus()
			return True
		return self.script_toLastMessage(gesture)

	# Move focus to the list of chat folders 
	@script(description=_("Move focus to list of chat folders"), gesture="kb:ALT+4")
	def script_to_tabs_folder(self, gesture):
		obj = self.saved_items.get("tabs folder")
		if obj and obj.location and obj.location.width:
			el = next((item for item in self.tabs_folder_element.children if State.SELECTED in item.states), None)
			if el: el.setFocus()
			else: message(_("Chat folder list not found"))
		else:
			list = self.getChatsListElement()
			if list:
				obj = list.previous
				self.saved_items.save("tabs folder", obj)
				el = next((item for item in obj.children if State.SELECTED in item.states), None)
				if el: el.setFocus()
				else: message(_("Chat folder list not found"))
			else: message(_("Chat folder list not found"))


	def _find_descendant(self, root, role=None, automation_id=None, max_depth=6):
		# Breadth-first walk for a descendant matching role and/or UIA automation id.
		queue_list = [(root, 0)]
		while queue_list:
			obj, depth = queue_list.pop(0)
			if depth > max_depth: continue
			try:
				if (role is None or obj.role == role) and (automation_id is None or obj.UIAAutomationId == automation_id):
					return obj
			except: pass
			try:
				child = obj.firstChild
				while child:
					queue_list.append((child, depth + 1))
					child = child.next
			except: pass
		return False

	def _find_deletion_primary_button(self, obj):
		"""Return the confirmation button from this delete popup only.

		Unigram's DeleteMessagesPopup and DeleteChatPopup do not share a stable
		child layout.  Start at the focused popup control and walk only a few
		ancestors, with the existing bounded descendant lookup at each level.
		"""
		for _ in range(5):
			if not obj:
				return False
			button = self._find_descendant(
				obj, Role.BUTTON, "PrimaryButton", max_depth=6
			)
			if button:
				return button
			try:
				obj = obj.parent
			except Exception:
				return False
		return False

	def _get_call_button_grid(self, foreground):
		# Return the VoipPage 1:1-call button grid (whose children include the named toggles
		# Mute/Camera/Screen and the unnamed hang-up button), or None when we are not in a
		# 1:1 call window. Used to tell a 1:1 call apart from a group call and from the story
		# viewer, which has its own unrelated "Mute" button.
		mute = self._find_descendant(foreground, automation_id="Mute", max_depth=14)
		if not mute: return None
		# VoipPage.xaml names the containing Grid "ActiveButtons". Following
		# parents is bounded and avoids recursively constructing every sibling
		# while NVDA is still creating the Mute object.
		return _find_ancestor_by_automation_id(mute, ("ActiveButtons",), max_depth=4)

	def _find_end_call_button(self, foreground):
		# 12.7's 1:1 hang-up button (VoipPage) has no automation id; it sits in the same grid
		# as Mute, wrapped in a Border, carrying the hang-up glyph \uea1f.
		grid = self._get_call_button_grid(foreground)
		if not grid: return None
		fallback = None
		queue_list = [grid]
		while queue_list:
			node = queue_list.pop(0)
			child = node.firstChild
			while child:
				try:
					if child.role == Role.BUTTON and child.UIAAutomationId not in ("Screen", "Camera", "Mute"):
						if child.firstChild and child.firstChild.name == "\uea1f": return child
						if not child.UIAAutomationId and fallback is None: fallback = child
				except: pass
				queue_list.append(child)
				child = child.next
		return fallback

	def _format_forum_topic_name(self, obj):
		# Speak a ForumTopicCell as "title, preview, time". 12.7 renamed the preview id
		# BriefInfo -> BriefText; guard the join so a partial cell never raises IndexError.
		labels = [label.name for label in obj.children if label.UIAAutomationId in ("TitleLabel", "BriefInfo", "BriefText", "TimeLabel")]
		if len(labels) >= 3: return ". ".join((labels[0], labels[2], labels[1]))
		if labels: return ". ".join(labels)
		return obj.name

	def _label_profile_identity(self, obj):
		# Build "<chat name>, <members/status>" for the profile-header identity button by
		# reading the neighbouring Title and Subtitle. Walk up from the button until we reach
		# a container that also holds the Subtitle (member count / status), grabbing the Title
		# on the way, so it works regardless of how the header is nested in the UIA tree.
		container = obj
		title_name = ""
		for _ in range(6):
			container = getattr(container, "parent", None)
			if not container: break
			if not title_name:
				title = self._find_descendant(container, automation_id="Title", max_depth=5)
				if title and title.name: title_name = title.name.strip()
			subtitle = self._find_descendant(container, automation_id="Subtitle", max_depth=5)
			if subtitle:
				parts = [part for part in (title_name, (subtitle.name or "").strip()) if part]
				if parts: return ", ".join(parts)
		return title_name

	def _looks_like_topic_item(self, obj):
		# A ForumTopicCell exposes child TextBlocks named TitleLabel + TimeLabel
		# (and BriefText/UnreadBadge). Detecting two of these is enough to be safe.
		try:
			ids = set()
			child = obj.firstChild
			depth = 0
			while child and depth < 30:
				try: ids.add(child.UIAAutomationId)
				except: pass
				child = child.next
				depth += 1
			return "TitleLabel" in ids and "TimeLabel" in ids
		except: return False

	def get_branch_list(self):
		# Older Unigram exposed the forum-topic list directly with UIAAutomationId == "TopicList".
		branch_list = next((item for item in self.getElements() if item.role == Role.LIST and item.UIAAutomationId == "TopicList"), False)
		if branch_list: return branch_list
		# Unigram 12.x renamed it: the ForumView is "TopicListPresenter" and the inner ListView is "ScrollingHost".
		presenter = next((item for item in self.getElements() if item.UIAAutomationId == "TopicListPresenter"), False)
		if presenter:
			branch_list = self._find_descendant(presenter, Role.LIST, "ScrollingHost")
			if branch_list and branch_list.firstChild: return branch_list
		# Forum group opened from the chat list shows ForumTopicCell items in a normal ListView.
		# Walk every top-level list and pick the first one whose first child looks like a topic cell.
		for item in self.getElements():
			try:
				if item.role == Role.LIST and item.firstChild:
					first = item.firstChild
					# Skip the chats list itself.
					if item.UIAAutomationId == "ChatsList": continue
					if first.name and first.name.startswith("forumTopic {"): return item
					if first.role == Role.LISTITEM and self._looks_like_topic_item(first): return item
			except: pass
		# Last resort: BFS through everything reachable to find a topic-cell list.
		try: root = api.getForegroundObject().lastChild.previous
		except: root = None
		if root:
			candidate = self._find_topic_list_recursive(root, max_depth=10)
			if candidate: return candidate
		return False

	def _find_topic_list_recursive(self, root, max_depth=10):
		queue_list = [(root, 0)]
		while queue_list:
			obj, depth = queue_list.pop(0)
			if depth > max_depth: continue
			try:
				if obj.role == Role.LIST and obj.UIAAutomationId != "ChatsList" and obj.firstChild:
					first = obj.firstChild
					if first.role == Role.LISTITEM and self._looks_like_topic_item(first):
						return obj
			except: pass
			try:
				child = obj.firstChild
				while child:
					queue_list.append((child, depth + 1))
					child = child.next
			except: pass
		return False

	@script(description=_("Move focus to the list of group threads"), gesture="kb:ALT+6")
	def script_move_focus_to_list_threads(self, gesture):
		branch_list = self.get_branch_list()
		if branch_list: branch_list.firstChild.setFocus()
		else: message(_("No list with threads was found"))

	def get_profile_panel(self):
		list = self.profile_panel_element
		if not list or not list.location.width:
			list = next((item for item in self.getElements() if (item.role == Role.LIST and item.UIAAutomationId == "ScrollingHost" and item.firstChild and item.firstChild.UIAAutomationId in ("Photo", "Segments")) or (item.role == Role.LINK and item.UIAAutomationId == "Photo" and item.next.UIAAutomationId == "Title")), None)
		if not list:
			return False
		if list.UIAAutomationId == "Photo":
			# If the profile does not contain any tabs, then the focus is set to the profile photo
			return list
		self.profile_panel_element = list
		list2 = list.firstChild
		for i in range(15):
			if list2.role == Role.LIST:
				# Now we find the selected element to set focus on it
				return next((item for item in list2.children if State.SELECTED in item.states), list2.firstChild)
			else: list2 = list2.next
		return list.firstChild

	# Move focus to open profile
	@script(description=_("Move focus to open profile"), gesture="kb:ALT+5")
	def script_to_open_prifile(self, gesture):
		profile_panel = self.get_profile_panel()
		if profile_panel: profile_panel.setFocus()
		else: message(_("There is no open profile"))

	# Announces the profile name and status in an open chat
	@script(description=_("Announce the name and status of an open chat"), gesture="kb:ALT+T")
	def script_read_prifile_name(self, gesture):
		if scriptHandler.getLastScriptRepeatCount() == 1:
			if Title_change_tracking.toggle(self.saved_items): message(_("Chat activity tracking is enabled"))
			else: message(_("Chat activity tracking is disabled"))
			return
		isGroupCall = False
		title = False
		obj = self.saved_items.get("profile name")
		if obj and obj.location.width != 0:
			title = obj
			message(obj.name)
		for item in self.getElements():
			if not title and item.role == Role.BUTTON and item.UIAAutomationId == "Profile":
				message(item.name)
				title = item
			elif item.role == Role.LINK and item.UIAAutomationId == "GroupCall": isGroupCall = item.firstChild.name
		if title:
			self.saved_items.save("profile name", title)
			if isGroupCall: message(isGroupCall)
		else: message(_("No open chat"))

	# Go to "unread messages" label
	@script(description=_("Move focus to 'unread messages' label"), gesture="kb:ALT+3")
	def script_goToTheLastUnreadMessage(self, gesture):
		messages = self.getMessagesElement()
		try: lastObj = messages.lastChild
		except:
			if not messages: message(_("No open chat"))
			elif not messages.lastChild: message(_("This chat is empty"))
			return False
		targetButton = False
		while lastObj:
			if lastObj.firstChild.role== Role.BUTTON  and lastObj.firstChild.firstChild.next.name == "\ue0e5":
				targetButton = lastObj
				break
			else: lastObj = lastObj.previous
		if targetButton: targetButton.setFocus()
		else: message(_("There are no unread messages in this chat"))

	# Call if it's a contact, or enter a voice chat if it's a group
	@script(description=_("Call if it's a contact, or enter a voice chat if it's a group"), gesture="kb:shift+alt+C")
	def script_call(self, gesture):
		try: targetButton = next((item for item in self.getElements() if (item.role == Role.BUTTON and item.UIAAutomationId == "Call") or (item.role == Role.LINK and item.UIAAutomationId == "GroupCall") or (item.next and item.next.UIAAutomationId == "Audio" and item.firstChild and item.firstChild.UIAAutomationId == "TitleInfo") ), False)
		except: targetButton =False
		if targetButton: targetButton.doAction()
		else: message(_("Call unavailable"))

	# Make a video call if it's a contact
	@script(description=_("Press the video call button"), gesture="kb:shift+alt+V")
	def script_videoCall(self, gesture):
		targetButton = next((item for item in self.getElements() if item.role == Role.BUTTON and item.UIAAutomationId == "VideoCall"), False)
		if targetButton: targetButton.doAction()
		else: message(_("Video call not available"))

	# Function to open instant view
	@script(description=_("Press \"Instant view\" button, if it is included in the current message"), gesture="kb:ALT+Q")
	def script_instantIew(self, gesture):
		obj = api.getFocusObject()
		if not self.is_message_object(obj): return
		targetButton = next((item.next for item in obj.children if item.UIAAutomationId == "TextBlock" and item.next.lastChild and item.next.lastChild.UIAAutomationId == "Button"), False)
		if targetButton:
			targetButton.doAction()
			targetList = next((item for item in self.getElements() if item.role == Role.LIST and item.UIAAutomationId == "ScrollingHost"), False)
			if targetList:
				item = next((item for item in targetList.children if item.name != ""), None)
				if item: item.setFocus()
		else: message(_("Button not found"))

	# End a call, decline call, or leave a voice chat
	def script_callCancellation(self, gesture):
		# Invoked from the GlobalPlugin ALT+N handler when there is no incoming-call toast,
		# i.e. to end an ongoing 1:1 call or leave a group voice chat.
		foreground = api.getForegroundObject()
		# 1:1 call: the hang-up button carries no automation id, so locate it positionally.
		targetButton = self._find_end_call_button(foreground) if foreground else None
		if not targetButton:
			# Group voice chat: the Leave button is named.
			targetButton = self._find_descendant(foreground, Role.BUTTON, "Leave", max_depth=14) if foreground else False
		if targetButton:
			lastFocus = api.getFocusObject()
			message(targetButton.name)
			self.fixedDoAction(targetButton)
			try: lastFocus.setFocus()
			except: pass

	# Mute/unmute the microphone
	@script(description=_("Press \"Mute/unmute microphone\" button"), gesture="kb:ALT+A")
	def script_microphone(self, gesture):
		obj = api.getFocusObject()
		foreground = api.getForegroundObject()
		# 1:1 call window (VoipPage): the mic toggle is x:Name="Mute" (checked == muted).
		grid = self._get_call_button_grid(foreground) if foreground else None
		if grid:
			mute = next((child for child in grid.children if child.UIAAutomationId == "Mute"), None)
			if mute:
				# The toggle flips on click, so announce the state it flips to.
				muted = State.PRESSED in mute.states or State.CHECKED in mute.states
				self.fixedDoAction(mute)
				obj.setFocus()
				new_name = _("Microphone on") if muted else _("Microphone muted")
				_announce_call_state_later(new_name)
				return
		# Group voice chat (GroupCallPage): mic button x:Name="Audio", status label "AudioInfo".
		audio = self._find_descendant(foreground, automation_id="Audio", max_depth=14) if foreground else False
		info = self._find_descendant(foreground, automation_id="AudioInfo", max_depth=14) if foreground else False
		if audio and info:
			audio.doAction()
			obj.setFocus()
			_announce_call_state_later(info.name)
			return
		message(_("Microphone button not found"))

	# Turn off/on the camera
	@script(description=_("Press \"Enable/disable camera\" button"), gesture="kb:ALT+V")
	def script_video(self, gesture):
		obj = api.getFocusObject()
		foreground = api.getForegroundObject()
		# 1:1 call window (VoipPage): the camera toggle is x:Name="Camera" (checked == on).
		grid = self._get_call_button_grid(foreground) if foreground else None
		if grid:
			camera = next((child for child in grid.children if child.UIAAutomationId == "Camera"), None)
			if camera:
				on = State.PRESSED in camera.states or State.CHECKED in camera.states
				self.fixedDoAction(camera)
				obj.setFocus()
				new_name = _("Camera off") if on else _("Camera on")
				_announce_call_state_later(new_name)
				return
		# Group voice chat (GroupCallPage): camera button x:Name="Video", status label "VideoInfo".
		video = self._find_descendant(foreground, automation_id="Video", max_depth=14) if foreground else False
		info = self._find_descendant(foreground, automation_id="VideoInfo", max_depth=14) if foreground else False
		if video and info:
			video.doAction()
			obj.setFocus()
			try:
				if video.firstChild and video.firstChild.name == "\ue964": new_name = _("Camera on")
				elif video.firstChild and video.firstChild.name == "\ue963": new_name = _("Camera off")
				else: new_name = info.name
			except Exception:
				new_name = info.name
			_announce_call_state_later(new_name)
			return
		message(_("Camera button not found"))

	# Copy the focused link to the clipboard. For anything else we defer to Unigram's own
	# Ctrl+C, so the shortcut is never handled twice (Unigram can't copy just a link, and
	# its copy does not apply while the focus is on a link, so the two no longer conflict).
	@script(description=_("Copy the message if it contains text. If the focus is on a link, the link will be copied"), gesture="kb:control+C")
	def script_copyMessage(self, gesture):
		obj = api.getFocusObject()
		if not (obj.parent and obj.parent.UIAAutomationId in ("Message", "TextBlock")):
			# Not on a link: let Unigram perform its native copy so it isn't done twice.
			gesture.send()
			return
		textMessage = obj.name
		if textMessage:
			api.copyToClip(textMessage.strip())
			message(_("Link copied"))
		else: message(_("This message does not contain text"))

	# Copy message via context menu
	# @script(description=_("Copy messages with formatting preserved"), gesture="kb:control+shift+C")
	def script_copy(self, gesture):
		self.activate_option_for_menu((icons_from_context_menu["copy"]), "Messages")

	# Show message text in popup window
	# @script(description=_("Show message text in popup window"), gesture="kb:ALT+C")
	def _script_show_text_message(self, gesture):
		obj = api.getFocusObject()
		if not self.is_message_object(obj): return False
		textMessage = next((item.name for item in obj.children if item.UIAAutomationId in ("TextBlock", "Message", "Question")), False)
		if textMessage: TextWindow(textMessage.strip(), _("message text"), readOnly=False)
		else: message(_("This message does not contain text"))

	# Move the focus to the message input field. If the focus is already in this field, then move it to the last element that had focus before this field
	@script(description=_("Move the focus to the edit field. If the focus is already in the edit field, then after pressing the hotkey, it will move to where it was before"), gesture="kb:ALT+D")
	def script_moveFocusToTextMessage(self, gesture):
		obj = api.getFocusObject()
		lastFocusObject = self.saved_items.get("last focus object")
		if (obj.role == Role.EDITABLETEXT and obj.UIAAutomationId == "TextField") or (obj.role == Role.BUTTON and obj.UIAAutomationId == "ButtonAction"):
			if lastFocusObject and lastFocusObject.location: lastFocusObject.setFocus()
			return
		targetButton = self.saved_items.get("message box")
		if not targetButton or not targetButton.location or not targetButton.location.width:
			targetButton = False
			for item in reversed(self.getElements()):
				if item.role == Role.EDITABLETEXT and item.UIAAutomationId == "TextField":
					targetButton = item
					self.saved_items.save("message box", item)
					break
		if targetButton: targetButton.setFocus()
		elif lastFocusObject and lastFocusObject.location : lastFocusObject.setFocus()
		else: message(_("Message input field not found"))

	# Press the "Attach media" button
	@script(description=_("Press \"Attach file\" button"), gesture="kb:control+shift+A")
	def script_add_files(self, gesture):
		button = next((item for item in self.getElements() if item.UIAAutomationId and item.UIAAutomationId == "ButtonAttach"), None)
		if button: button.doAction()
		else: message(_("Button not found"))

	# Press the "New Conversation" button
	@script(description=_("Press \"New conversation\" button"), gesture="kb:control+N")
	def script_new_conversation(self, gesture):
		button = next((item for item in self.getElements() if item.UIAAutomationId and item.UIAAutomationId == "ComposeButton"), None)
		if button: button.doAction()
		else: message(_("Button not found"))

	# Press the "More options" button in an open chat
	# @script(description=_("Press \"More Options\" button in an open chat, voice chat, or call window"), gesture="kb:ALT+O")
	def script_showMoreOptions(self, gesture):
		labels_for_button = labels_for_button_more_options.get(conf.get("lang"), labels_for_button_more_options["en"])
		targetButton = next((item for item in self.getElements() if item.role == Role.BUTTON and (item.UIAAutomationId in ("Options", "Menu", "Settings") or item.name in labels_for_button) ), False)
		if targetButton: targetButton.doAction()
		else: message(_("Button not found"))

	# Open navigation menu
	@script(description=_("Open navigation menu"), gesture="kb:ALT+M")
	def script_showMenu(self, gesture):
		try:
			targetButton = next((item for item in self.getElements() if item.UIAAutomationId == "Photo" and item.role == Role.TOGGLEBUTTON), False)
		except: targetButton = False
		if targetButton: targetButton.doAction()
		else: message(_("Navigation menu not available"))

	# Function to open the profile of the current chat
	@script(description=_("Open current chat profile"), gesture="kb:alt+shift+P")
	def script_openProfile(self, gesture):
		profile = self.saved_items.get("profile name")
		if not profile or profile.location.width == 0:
			# If the element was not cached, then we will try to find it in the window
			profile = next((item for item in self.getElements() if item.role ==Role.BUTTON and item.UIAAutomationId == "Profile"), None)
			if profile:
				# If we managed to find the element, then we cache it
				self.saved_items.save("profile name", profile)
		if profile and profile.location.width != 0:
			self.isOpenProfile = api.getFocusObject()
			profile.doAction()
		else:
			message(_("No open chat"))

	def _announceVoiceRecordingTransition(self, transition):
		indicator = conf.get("voiceMessageRecordingIndicator")
		if not transition or indicator == "none":
			return
		if transition == "sent":
			if indicator == "audio":
				winsound.PlaySound(baseDir+"send_voice_message.wav", winsound.SND_ASYNC | winsound.SND_NOSTOP)
			else:
				message(_("Record sent"))
			return
		if transition == "canceled":
			if indicator == "audio":
				winsound.PlaySound(
					baseDir+"cancel_voice_message_recording.wav",
					winsound.SND_ASYNC | winsound.SND_NOSTOP,
				)
			else:
				message(_("Recording canceled"))
			return
		if transition != "start":
			return

		# The monitor already holds the record button. Do not rescan Unigram's UIA
		# tree here, because doing so blocks NVDA while recording begins.
		try:
			button = self._voiceRecordingButton
			isVideo = bool(button and State.PRESSED in button.states)
		except Exception as error:
			log.debug("Could not inspect Unigram voice-message recording mode: %r" % error)
			isVideo = False
		if indicator == "audio":
			filename = "start_recording_video_message.wav" if isVideo else "start_recording_voice_message.wav"
			winsound.PlaySound(baseDir+filename, winsound.SND_ASYNC)
		else:
			message(_("Video") if isVideo else _("Audio"))

	def _scheduleVoiceRecordingPoll(self):
		if not self._voiceRecordingMonitorRunning:
			return
		import core

		core.callLater(round(_VOICE_RECORDING_POLL_INTERVAL * 1000), self._pollVoiceRecordingState)

	def _getVoiceRecordingButton(self, focus):
		button = self._voiceRecordingButton
		if is_recording_button(button):
			return button
		if is_recording_button(focus):
			self._voiceRecordingButton = focus
			return focus
		# getElements is comparatively cheap but can fail while a packaged app is
		# starting. Try it only once per focused object, never on every poll.
		if focus is self._voiceRecordingDiscoveryFocus:
			return None
		self._voiceRecordingDiscoveryFocus = focus
		button = next((item for item in self.getElements() if is_recording_button(item)), None)
		if button:
			self._voiceRecordingButton = button
		return button

	def _getVoiceRecordingLastMessage(self):
		try:
			messages = self.getMessagesElement()
			if not messages:
				return None, None
			lastMessage = messages.lastChild
			return message_marker(lastMessage), lastMessage
		except Exception:
			return None, None

	def _handleVoiceRecordingTransition(self, transition):
		if transition == "start":
			try:
				button = self._voiceRecordingButton
				isVideo = bool(button and State.PRESSED in button.states)
			except Exception:
				isVideo = False
			baseline, _lastMessage = self._getVoiceRecordingLastMessage()
			self._voiceRecordingOutcome.started(baseline, isVideo)
			self._announceVoiceRecordingTransition("start")
		elif transition == "stopped":
			self._voiceRecordingOutcome.stopped()

	def _pollVoiceRecordingOutcome(self):
		if not self._voiceRecordingOutcome.pending:
			return
		marker, lastMessage = self._getVoiceRecordingLastMessage()
		markerChanged = (
			self._voiceRecordingOutcome.baseline is not None
			and marker != self._voiceRecordingOutcome.baseline
		)
		transition = self._voiceRecordingOutcome.observe(
			marker,
			markerChanged and is_recorded_message(lastMessage, self._voiceRecordingOutcome.video),
		)
		if transition:
			log.info("Unigram voice-message recording outcome: %s" % transition)
			self._announceVoiceRecordingTransition(transition)

	def _pollVoiceRecordingState(self):
		if not self._voiceRecordingMonitorRunning:
			return
		try:
			focus = api.getFocusObject()
			if getattr(focus, "appModule", None) is not self:
				return
			# Calls run in separate WindowEx instances. A cached chat control can
			# become an expensive disconnected UIA object there, and getElements()
			# would scan the call surface every 200 ms. Voice-message monitoring is
			# meaningful only in the window that owns ChatsList/Messages/TextField.
			if not self._is_main_window_object(focus):
				self._voiceRecordingDiscoveryFocus = None
				return
			self._pollVoiceRecordingOutcome()
			button = self._getVoiceRecordingButton(focus)
			active = recording_button_state(button)
			if button is not None and active is None:
				# A chat change can detach the cached UIA object. Rediscover once for
				# this focus; a second failure is not retried on every poll.
				self._voiceRecordingButton = None
				self._voiceRecordingDiscoveryFocus = None
				button = self._getVoiceRecordingButton(focus)
				active = recording_button_state(button)
			if active is None:
				self._voiceRecordingButton = None
				return
			transition = self._voiceRecordingState.visibilityChanged(active)
			if transition:
				log.info("Unigram voice-message recording transition: %s" % transition)
			self._handleVoiceRecordingTransition(transition)
		except Exception as error:
			log.debug("Could not monitor Unigram voice-message recording UI: %r" % error)
		finally:
			self._scheduleVoiceRecordingPoll()

	# Processing the message that got into focus
	def action_message_focus(self, obj):
		keywords = obj.keywords
		sender = ""
		# forward = ""
		header = False
		admin_label = ""
		reactions = []
		sender_message = self.sender_message or ""
		item = obj.firstChild
		while item:
			if item.UIAAutomationId in ("Question", "QuestionText"):
				# Processing messages containing a poll
				options, votes = "", ""
				for el in obj.children:
					if el.UIAAutomationId == "Votes": votes = ". "+el.name+". "
					elif el.role == Role.TOGGLEBUTTON and el.firstChild.role == Role.PROGRESSBAR:
						if el.childCount == 3: options += self.processing_of_answer_options_in_surveys(el)
						elif el.childCount == 2: options+=el.children[1].name+", "
				if options: options = _("Answer options")+": "+options
				obj.name = obj.name.replace(item.name+", ", item.name+votes+options)
			elif conf.get("actionDescriptionForLinks")  and item.role == Role.LINK and len(item.name) > 30 and not item.UIAAutomationId and item.firstChild.UIAAutomationId == "Label":
				# Processing the description of the link contained in the message
				description = item.name.strip()
				if not conf.get("voiceFullDescriptionOfLinkToYoutube") and description.startswith("YouTube "):
					description = description.split("\n")
					description = "\n".join(description[:2])
				# We escape all symbols \
				description = description.replace("\\", "").replace("http:\\", "\\\\")
				obj.name =re.sub(r"[.,]?{}|{}".format(keywords[3], keywords[2]), r". \n{}\g<0>".format(description), obj.name)
				obj.name =re.sub(r"(https?://\S+)\?[^\s,]+", r"\g<1>", obj.name)
			elif item.UIAAutomationId == "Subtitle" and len(item.name) < 15 and " / " in item.name:
				# Checking if a message is a voice message
				obj.name = item.name+", "+obj.name.replace(item.name[-5:], "")
			elif item.UIAAutomationId == "HeaderLabel": header = item
			item = item.next
		

		# Checking if a message is a call
		try:
			if obj.firstChild.role == Role.LINK and not obj.firstChild.name and obj.childCount == 7 and obj.children[1].UIAAutomationId == "TitleLabel" and obj.children[3].role == Role.STATICTEXT:
				a = obj.children[1].name
				b = ",".join(obj.children[3].name.split(",")[1:])
				obj.name = obj.name.replace(a, a+b)
				obj.index_last_part_in_message += len(b)
		except: pass

		# Checking Whether to Add a Message Sender Name
		profile_name = self.saved_items.get("profile name")
		if conf.get("saySenderName") in ("sent", "all") and sender_message == "send" and not header: sender = _("You")+".\n"
		elif conf.get("saySenderName") in ("received", "all") and profile_name and obj.simpleFirstChild.UIAAutomationId not in ("Photo", "1HeaderLabel", "PhotoRoot") and obj.simpleFirstChild.location.left - obj.location.left < 35 and not header: sender = profile_name.firstChild.name+".\n"
		
		# Check the status of the message, whether it is read and sent
		# Checking only sent messages
		if keywords[0] in self.end_text:
			# If the message is read, delete information about it
			obj.name = obj.name.replace(keywords[0], ".", -1)
		elif keywords[1] in self.end_text:
			# If the message is not read, check whether it is necessary to display information about it
			if (sender_message == "received") or (profile_name and profile_name.childCount == 1):
				obj.name = obj.name.replace(keywords[1], ".", -1)
			elif conf.get("unreadBeforeMessageContent"):
				obj.name = obj.name.replace(keywords[1], ".", -1)
				obj.name = keywords[1][2:]+". "+obj.name
		if not conf.get("announce_endthe_message") and obj.index_last_part_in_message:
			obj.name = obj.name[:obj.index_last_part_in_message]
		if keywords[3] in self.end_text:
			# Removal of the phrase "administrator" and the phrase "owner" in messages
			list_text = obj.name.split("\n")
			key_phrases = phrase_administrator_in_message.get(conf.get("lang"), phrase_administrator_in_message["en"])
			en_key_phrases = phrase_administrator_in_message["en"]
			if not conf.get("notify administrators in messages") and len(list_text) > 1 and list_text[1] in (", "+key_phrases[0]+". \r", ", "+key_phrases[1]+". \r", ", "+en_key_phrases[0]+". \r", ", "+en_key_phrases[1]+". \r"):
				del list_text[1]
				obj.name = "\n".join(list_text)


		obj.name = sender+obj.name
		if conf.get("messageHeaderAtTheEnd"):
			content_anchor = extract_message_text(obj)
			if content_anchor:
				obj.name = move_message_header_after_content(obj.name, content_anchor)
		# Check if a message is selected
		selected_prefix = _("Selected")+". "
		if State.SELECTED in obj.states and not obj.name.startswith(selected_prefix): obj.name = selected_prefix+obj.name
		return obj.name

	# Processing the focused element from the list of chats
	def actionChatElementInFocus(self, obj):
		# If the user does not want to change the order of elements in the chat name, then we immediately terminate the function to improve the response speed
		if conf.get("voiceTypeAfterChatName") == "beforeName": return obj.name
		item = obj.firstChild
		while item:
			if item.UIAAutomationId == "TitleLabel":
				title = item.name
				type = obj.name.split(", ")[0] if not obj.name.startswith(title) else ""
				if not type: break
				elif type and conf.get("voiceTypeAfterChatName") == "afterName":
					obj.name = obj.name.replace(type+", "+title, title+", "+type, 1)
				elif type and conf.get("voiceTypeAfterChatName") == "don'tVoice":
					obj.name = obj.name.replace(type+", ", "", 1)
				break
			item = item.next
		return obj.name

	# Change the announce level of progress bars
	@script(description=_("Toggle progress bar announcements"), gesture="kb:ALT+U")
	def script_toggleVoicingPerformanceIndicators(self, gesture):
		current = conf.get("voicingPerformanceIndicators")
		if current == "none":
			conf.set("voicingPerformanceIndicators", "upload_download")
			if not File_transfer_progress_tracking.active: File_transfer_progress_tracking.start()
			message(_("Announce progress bars only during upload and download"))
		elif current == "upload_download":
			conf.set("voicingPerformanceIndicators", "all")
			if not File_transfer_progress_tracking.active: File_transfer_progress_tracking.start()
			message(_("Announce all progress bars"))
		else:
			conf.set("voicingPerformanceIndicators", "none")
			File_transfer_progress_tracking.stop()
			message(_("Do not announce any progress bars"))

	def script_reviewRecentMessage(self, gesture):
		try: index = int(gesture.mainKeyName[-1])
		except (AttributeError, ValueError): return
		if index == 0: index = 10
		obj = self.getMessagesElement()
		if not obj:
			message(_("No open chat"))
			return
		target = obj.lastChild
		if not target:
			message(_("This chat is empty"))
			return
		i = 0
		while target:
			child = target.firstChild
			if child.role not in (Role.BUTTON, Role.GROUPING):
				i += 1
				if i == index:
					message(self.action_message_focus(target))
					api.setNavigatorObject(target)
					break
			target = target.previous
		if i < index:
			message(_("This chat is empty"))
			return


	def event_show(self, obj, nextHandler):
		try:
			if getattr(self, "isUnigramWindow", False):
				self._remember_messages_button(obj)
				if is_recording_button(obj):
					self._voiceRecordingButton = obj
					self._voiceRecordingDiscoveryFocus = None
				elif obj.UIAAutomationId == "ElapsedLabel":
					transition = self._voiceRecordingState.elapsedChanged(obj.name)
					self._handleVoiceRecordingTransition(transition)
		finally:
			nextHandler()

	def event_nameChange(self, obj, nextHandler):
		try:
			if getattr(self, "isUnigramWindow", False) and obj.UIAAutomationId == "ElapsedLabel":
				transition = self._voiceRecordingState.elapsedChanged(obj.name)
				self._handleVoiceRecordingTransition(transition)
		finally:
			nextHandler()

	def event_hide(self, obj, nextHandler):
		try:
			if (
				getattr(self, "isUnigramWindow", False)
				and is_recording_button(obj)
				and obj is self._voiceRecordingButton
			):
				self._voiceRecordingButton = None
				self._voiceRecordingDiscoveryFocus = None
			elif getattr(self, "isUnigramWindow", False) and obj.UIAAutomationId == "ElapsedLabel":
				self._handleVoiceRecordingTransition(self._voiceRecordingState.hidden())
		finally:
			nextHandler()

	def event_focusEntered(self, obj, nextHandler):
		"""Suppress the transient Messages-list ancestor announcement.

		Unigram recycles the virtualized message containers while navigating.  On
		the affected transitions NVDA sees ``Messages`` as a newly entered list
		ancestor and would announce "list" before the focused message.  Handle
		that exact ancestor before NVDA's object-level event queues speech.
		"""
		if not getattr(self, "isUnigramWindow", False):
			fallback = getattr(self, "_fallbackAppModule", None)
			if fallback and hasattr(fallback, "event_focusEntered"):
				try:
					fallback.event_focusEntered(obj, nextHandler)
					return
				except Exception:
					pass
			nextHandler()
			return
		try:
			if obj.role == Role.LIST and getattr(obj, "UIAAutomationId", "") == "Messages":
				return
		except Exception:
			pass
		nextHandler()

	# Focus change tracking
	def event_gainFocus(self, obj, nextHandler):
		if is_recording_button(obj):
			self._voiceRecordingButton = obj
		if not getattr(self, "isUnigramWindow", False):
			fallback = getattr(self, "_fallbackAppModule", None)
			if fallback and hasattr(fallback, "event_gainFocus"):
				try:
					fallback.event_gainFocus(obj, nextHandler)
					return
				except Exception:
					pass
				nextHandler()
				return
		self._remember_messages_button(obj)
		is_main_window = self._classify_window_surface(obj) == "main"
		if is_main_window and conf.get("automatically announce new messages") and Chat_update.pouse:
			# Since the timer is suspended when the program window is minimized, it needs to be restored as soon as the focus is set on some element in the window
			Chat_update.restore(self)
		if is_main_window and conf.get("automatically announce activity in chats") and Title_change_tracking.pouse:
			# Since the timer is suspended when the program window is minimized, it needs to be restored as soon as the focus is set on some element in the window
			Title_change_tracking.restore(self.saved_items)
		if is_main_window and conf.get("play_typing_sound") and Typing_sound_tracking.pouse:
			Typing_sound_tracking.restore(self.saved_items)
		if not File_transfer_progress_tracking.active:
			try:
				percentage = None
				if File_transfer_progress_tracking._is_transfer_button(obj):
					percentage = File_transfer_progress_tracking._parse_percentage(
						File_transfer_progress_tracking._read_fresh_value(obj)
					)
				if percentage is not None and percentage < 100:
					File_transfer_progress_tracking.start()
			except Exception:
				pass
		if self.isSkipName:
			speech.cancelSpeech()
			self.isSkipName -= 1
			return True
		elif self.isOpenProfile:
			self.isOpenProfile = False
			panel = next((item for item in self.getElements() if item.UIAAutomationId == "ScrollingHost"), None)
			if panel:
				self.profile_panel_element = panel
				panel.firstChild.setFocus()
		elif self.execute_context_menu_option:
			if self._handle_pending_context_menu_focus(obj, nextHandler):
				return
		elif self.isRecord:
			self.isRecord.setFocus()
			self.isRecord = False
			self.isSkipName = 1
			return True
		elif self.isDelete and self.deleteMessageAndChat(obj):
			return
		if obj.role == Role.LISTITEM:
			speech.cancelSpeech()
			if self.is_message_object(obj):
				self.saved_items.save("last focus object", obj)
				obj.name = self.action_message_focus(obj)
			elif _is_chat_list_item(obj):
				self.saved_items.save("last focused chat", obj)
				obj.name = self.actionChatElementInFocus(obj)
			elif obj.parent.UIAAutomationId == "ScrollingHost":
				if conf.get("messageHeaderAtTheEnd"):
					content_anchor = self._profile_media_content_anchor(obj)
					if content_anchor is not None:
						obj.name = move_profile_header_after_content(obj.name, content_anchor)
				if obj.name.startswith("forumTopic {\n  info = forumTopicInfo {"):
					obj.name = self._format_forum_topic_name(obj)
				elif obj.name == "" and obj.childCount != 0:
					for item in obj.children: obj.name+=item.name
				elif obj.name.startswith("inlineQueryResult"):
					# Processing inline results
					name = [item.name for item in obj.children if item.name != ""]
					obj.name = ". ".join(name)
			elif obj.name == "Unigram.ViewModels.MessageViewModel": obj.name = obj.firstChild.name
			elif obj.name.startswith("EETypeRva"): obj.name = ", ".join([item.name for item in obj.children[1:]])
			elif obj.name == "Unigram.Entities.StoragePhoto": obj.name = _("Image")
			elif obj.name == "Unigram.ViewModels.Folders.FilterFlag": obj.name = obj.children[1].name
			elif obj.name.startswith("chatTheme {"): obj.name = obj.firstChild.name
			elif obj.name.startswith("forumTopic {\n  info = forumTopicInfo {"):
				obj.name = self._format_forum_topic_name(obj)
		elif obj.role == Role.EDITABLETEXT:
			try:
				# If this message input field has a composer header attached (reply or edit),
				# announce "Reply"/"Editing" instead of the usual "type a message" prompt.
				if obj.UIAAutomationId == "TextField":
					# The composer header's cancel button sits a few siblings before the field
					# (an extra ButtonMore/upload ring may come between), so scan back for it.
					cancel = obj.previous
					for step in range(5):
						if not cancel or cancel.UIAAutomationId == "ComposerHeaderCancel": break
						cancel = cancel.previous
					if cancel and cancel.UIAAutomationId == "ComposerHeaderCancel":
						# The reply/edit glyph sits just before the cancel button.
						glyph = cancel.previous
						for step in range(3):
							if not glyph or glyph.name in ("\uea4a", "\uea4b"): break
							glyph = glyph.previous
						if glyph and glyph.name == "\uea4b": obj.name = _("Editing")
						elif glyph and glyph.name == "\uea4a": obj.name = _("Reply")
			except: pass
		elif obj.role == Role.LINK:
			try:
				if obj.UIAAutomationId in ("Button", "Download") and obj.parent.parent.parent.UIAAutomationId == "Messages":
					# Announcing the name and size of the file when the focus is on the button to open or download this file
					def action(title, subtitle):
						arr = subtitle.split(" - ")
						for index, value in enumerate(arr):
							if ":" in value: arr[index] = _("Duration")+": "+arr[index]
							else: arr[index] = _("Size")+": "+arr[index]
						subtitle = ". ".join(arr)
						return ": "+title+". "+subtitle
					if obj.next.UIAAutomationId == "Title" and obj.next.next.UIAAutomationId == "Subtitle": obj.name += action(obj.next.name, obj.next.next.name)
					elif obj.next.next.UIAAutomationId == "Title" and obj.next.next.next.UIAAutomationId == "Subtitle": obj.name += action(obj.next.next.name, obj.next.next.next.name)
				elif obj.parent.UIAAutomationId in ("TextBlock", "Message"): speech.cancelSpeech()
			except: pass
		elif obj.role == Role.BUTTON:
			try:
				# Add a label to unmute the microphone on a voice call
				# Add a label to turn on the camera on a voice call
				if obj.UIAAutomationId == "Audio" and obj.firstChild.name == "\ue720" and obj.next.UIAAutomationId == "AudioInfo": obj.name = obj.next.name
				elif obj.UIAAutomationId == "Video" and obj.firstChild.name == "\ue963": obj.name = _("Enable video")
				elif obj.UIAAutomationId == "Video" and obj.firstChild.name == "\ue964": obj.name = _("Disable video")
			except: pass
		elif obj.role == Role.TOGGLEBUTTON:
			try:
				# The voice/video message record button carries no text of its own, so NVDA
				# would otherwise announce its automation id as "Tn voice message". Give it a
				# clear label; while recording is in progress also read the elapsed time shown
				# next to it (a pressed toggle means video-note mode, otherwise a voice message).
				if obj.UIAAutomationId == "btnVoiceMessage":
					isVideo = State.PRESSED in obj.states
					if obj.next and obj.next.UIAAutomationId == "ElapsedLabel":
						label = _("Recording a video message, elapsed time") if isVideo else _("Recording a voice message, elapsed time")
						obj.name = label+" "+re.split(r"[.,]", obj.next.name)[0]
					else:
						obj.name = _("Record a video message") if isVideo else _("Record a voice message")
				else:
					# Checking if a toggle button is an answer option in a vote
					if "reactionTypeEmoji {" in obj.name:
						obj.name = re.sub(r"^(.+)reactionTypeEmoji.+\"(.)\".+", r"\g<1>\g<2>", obj.name, flags=re.S)
					if obj.firstChild.UIAAutomationId == "Loading"  and obj.lastChild.UIAAutomationId == "Votes" and obj.childCount == 3: obj.name = self.processing_of_answer_options_in_surveys(obj)
			except: pass
		# In the profile-page header, the verified-badge button (IdentityRoot) is the next
		# focusable element after the chat name but carries no text of its own, so NVDA would
		# otherwise announce its automation id ("Identity root"). Replace that with the chat
		# name and member count read from the neighbouring Title and Subtitle.
		if obj.UIAAutomationId == "IdentityRoot" and not obj.name:
			obj.name = self._label_profile_identity(obj)
		# In a 1:1 call the Mute/Camera toggles keep a static name, so make the announced label
		# reflect the current state. Scope to the call button grid to avoid the story viewer's
		# own "Mute" button.
		if obj.UIAAutomationId in ("Mute", "Camera"):
			try:
				if _find_ancestor_by_automation_id(obj, ("ActiveButtons",), max_depth=4):
					on = State.PRESSED in obj.states or State.CHECKED in obj.states
					if obj.UIAAutomationId == "Mute": obj.name = _("Microphone muted") if on else _("Microphone on")
					else: obj.name = _("Camera on") if on else _("Camera off")
			except: pass
		if obj.name == "":
			if obj.firstChild and obj.firstChild.name in labels_in_buttons: # If the button contains an icon, check if the dictionary contains the label for that icon
				obj.name = labels_in_buttons[obj.firstChild.name]
			elif obj.UIAAutomationId in labels_for_buttons: # If the button has a label, separate it by words and assign it as the item name
				obj.name = labels_for_buttons[obj.UIAAutomationId]
			elif obj.UIAAutomationId:
				obj.name = ''.join(' ' + char.lower() if char.isupper() else char for char in obj.UIAAutomationId)
				obj.name = "".join(obj.name[1:]).capitalize()
			elif obj.childCount > 1:
				name = [item.name for item in obj.children if item.name != ""]
				obj.name = "/. ".join(name)
		nextHandler()

	# Processing item initialization
	def chooseNVDAObjectOverlayClasses(self, obj, clsList):
		if not getattr(self, "isUnigramWindow", False):
			fallback = getattr(self, "_fallbackAppModule", None)
			if fallback and hasattr(fallback, "chooseNVDAObjectOverlayClasses"):
				try: fallback.chooseNVDAObjectOverlayClasses(obj, clsList)
				except Exception: pass
			return
		try:
			self._remember_messages_button(obj)
			# This hook runs for every materialized UIA object. Only stable marker
			# objects can identify the chat window without a parent walk; focused
			# descendants are handled once in event_gainFocus instead.
			if getattr(obj, "UIAAutomationId", "") in _WINDOW_SURFACE_AUTOMATION_IDS:
				self._classify_window_surface(obj)
			if is_recording_button(obj):
				self._voiceRecordingButton = obj
			if obj.role == Role.LISTITEM and obj.isFocusable:
				parent = obj.parent
				if parent.UIAAutomationId == "ChatFolders":
					self.tabs_folder_element = parent
					if conf.get("voiceFolderNames") and State.SELECTED in obj.states: self.change_chats_folder(obj, parent.UIAAutomationId)
					return True
				elif parent.UIAAutomationId == "Navigation":
					clsList.insert(0, SettingsPanelListItem)
					return True
				elif _is_chat_list_item(obj):
					clsList.insert(0, ChatListItem)
					return
				elif parent.UIAAutomationId == "TopicList": return
				elif obj.name.startswith("forumTopic {"): return
				# We check whether the element contains phrases that will help us identify it as a message.
				# Service and blank final messages can have no accessible name, but their
				# Message_item id and Messages-row ancestry still identify them reliably.
				keywords = keywordsInMessages.get(conf.get("lang"), keywordsInMessages["en"])
				name = (obj.name or "")[-200:]
				self.sender_message = "received" if keywords[3] in name else "send" if keywords[2] in name else ""
				self.end_text = name
				if (
					_is_message_list_item(obj)
					or self.sender_message
					or (parent.role == Role.LISTITEM and parent.location.width > 800)
				):
					clsList.insert(0, Message_list_item)
			elif conf.get("action_when_pressing_up_arrow_in_text_field") != "normal" and obj.role == Role.EDITABLETEXT and obj.UIAAutomationId == "TextField":
				# Add processing for pressing the up arrow key to the message input field
				clsList.insert(0, EditableText)
			elif obj.role == Role.BUTTON and obj.UIAAutomationId == "Profile":
				self.saved_items.save("profile name", obj)
			elif obj.UIAAutomationId in ("Audio", "Video"):
				clsList.insert(0, Audio_and_video_button)
			elif obj.UIAAutomationId in ("Mute", "Camera"):
				# VoipPage.xaml puts these toggles under ActiveButtons. Do not inspect
				# parent.children here: this hook runs while NVDA is constructing obj,
				# and sibling enumeration can recursively re-enter object creation.
				if _find_ancestor_by_automation_id(obj, ("ActiveButtons",), max_depth=4):
					clsList.insert(0, Audio_and_video_button)
			# elif obj.role == Role.BUTTON and obj.UIAAutomationId == "Explanation":
				# clsList.insert(0, ExplanationCorrectAnswerInQuiz)
			elif obj.UIAAutomationId == "Slider" and (obj.name == "Seek" or obj.role == Role.SLIDER):
				self.saved_items.save("slider", obj)
			elif (
				File_transfer_progress_tracking._is_transfer_button(obj)
				and File_transfer_progress_tracking._parse_percentage(
					File_transfer_progress_tracking._read_fresh_value(obj)
				) is not None
			):
				clsList.insert(0, File_transfer_progress_button)
			elif conf.get("voicingPerformanceIndicators") in ("none", "upload_download") and obj.role == Role.PROGRESSBAR:
				clsList.pop(0)
		except Exception as e: pass

	def deleteMessageAndChat(self, obj):
		pending = self.isDelete
		if not pending:
			return False
		state = pending["state"]
		if state == 1 and pending.get("nativeDelete", False):
			automation_id = str(getattr(obj, "UIAAutomationId", "") or "")
			if obj.role == Role.CHECKBOX and automation_id == "RevokeCheck":
				if not conf.get("confirmation_at_deletion"):
					speech.cancelSpeech()
				checked = State.CHECKED in obj.states
				if pending["isCompleteDeletion"] != checked:
					obj.doAction()
				primary_button = self._find_deletion_primary_button(obj)
				if primary_button:
					primary_button.doAction()
					pending["state"] = 2
				return True
			if obj.role == Role.BUTTON and automation_id == "PrimaryButton":
				if not conf.get("confirmation_at_deletion"):
					speech.cancelSpeech()
				obj.doAction()
				pending["state"] = 2
				return True
			# Delete can take several seconds to create its popup. Do not mistake a
			# composer, calendar, attachment, or other button for the delete action
			# while the dialog is still loading.
			return False
		if state == 1:
			automation_id = str(getattr(obj, "UIAAutomationId", "") or "")
			is_checkbox = obj.role == Role.CHECKBOX and automation_id == "CheckBox"
			is_primary_button = obj.role == Role.BUTTON and automation_id == "PrimaryButton"
			if not (is_checkbox or is_primary_button):
				return False
			if not conf.get("confirmation_at_deletion"):
				speech.cancelSpeech()
			targetButton = next(
				(x for x in pending.get("elements", []) if x.location and x.location.width),
				False,
			)
			if is_checkbox:
				# Check whether deletion for both sides must be toggled.
				checked = State.CHECKED in obj.states
				if (
					(pending["isCompleteDeletion"] and not checked)
					or (not pending["isCompleteDeletion"] and checked)
				):
					obj.doAction()
				primary_button = self._find_deletion_primary_button(obj)
				if not primary_button:
					self.isDelete = False
					return True
				primary_button.doAction()
			else:
				obj.doAction()
			if targetButton: targetButton.setFocus()
			elif pending["list"] == "messages": self.script_toLastMessage(False)
			elif pending["list"] == "chats": self.script_toChatList(False)
			pending["state"] = 2
			return True
		if state != 1:
			if pending["message"] == "audio": winsound.PlaySound(baseDir+"delete.wav", winsound.SND_ASYNC)
			else: message(pending["message"])
			# if self.isDelete["list"] == "messages": message(self.action_message_focus(obj))
			if pending["list"] == "messages": message(obj.name)
			elif pending["list"] == "chats": message(self.actionChatElementInFocus(obj))
			self.isDelete = False
			return True
		return False

	def _expire_native_delete(self, pending):
		"""Discard a native Delete request if Unigram never completes its popup flow."""
		if self.isDelete is pending:
			self.isDelete = False

	@script(description=_("Delete a message or chat"), gesture="kb:ALT+delete")
	def script_deletion(self, gesture):
		if not self.isDelete and not self.startDeleteMessage(False): gesture.send()
	@script(description=_("Delete message or chat from both sides"), gesture="kb:shift+delete")
	def script_completeDeletion(self, gesture):
		if not self.isDelete and not self.startDeleteMessage(True, useNativeDelete=True): gesture.send()
	@script(description=_("Switch to selection mode"), gesture="kb:control+space")
	def script_selectMessage(self, gesture):
		self.activate_option_for_menu((icons_from_context_menu["select"]), "Messages")
	@script(description=_("Forward message"), gesture="kb:ALT+F")
	def script_forwardMessage(self, gesture):
		self.activate_option_for_menu((icons_from_context_menu["forward"]), "Messages")
	@script(description=_("Mark a chat as read"), gesture="kb:ALT+shift+R")
	def script_readMessage(self, gesture):
		self.activate_option_for_menu((icons_from_context_menu["read"], icons_from_context_menu["unread"]), "ChatsList")
	@script(description=_("Save file as..."))
	def script_save_file(self, gesture):
		self.activate_option_for_menu((icons_from_context_menu["save_as"]), "Messages")
	@script(description=_("Pin a message or chat"))
	def script_attach(self, gesture):
		self.activate_option_for_menu((icons_from_context_menu["attach"], icons_from_context_menu["unpin"]))
	def _handle_pending_context_menu_focus(self, obj, nextHandler):
		pending = self.execute_context_menu_option
		if not pending:
			return False
		if pending.get("rawInvoked"):
			nextHandler()
			return True
		try:
			obj_role = obj.role
		except Exception:
			obj_role = None
		if obj_role == Role.MENUITEM:
			if _menu_item_has_icon(obj, pending["icons"]):
				self.execute_context_menu_option = False
				core.callLater(_CONTEXT_MENU_STEP_DELAY_MS, self._invoke_context_menu_item, obj)
				return True
		elif obj_role not in (Role.LINK, Role.BUTTON):
			# Unigram 12.9 can keep focus on transient popup windows and never expose
			# a focused MenuFlyoutItem. Probe those popup roots through raw UIA on
			# NVDA's MTA thread before calling the rest of the focus-event chain.
			# Some third-party event handlers can raise from nextHandler, but that
			# must not prevent this independent lookup from being scheduled.
			popup_roles = tuple(
				role
				for role in (
					getattr(Role, "WINDOW", None),
					getattr(Role, "POPUPMENU", None),
					getattr(Role, "MENU", None),
				)
				if role is not None
			)
			if obj_role in popup_roles:
				self._schedule_context_menu_raw_probe(obj, pending)
			nextHandler()
			return True
		# ReactionsMenuFlyout initially focuses a reaction HyperlinkButton. Its
		# OnPreviewKeyDown handler moves Down to the first real MenuFlyoutItem.
		self._arm_context_menu_timeout(pending, _CONTEXT_MENU_ACTIVITY_TIMEOUT_MS)
		if pending.get("navigationScheduled"):
			return True
		pending["moves"] += 1
		if pending["moves"] <= _CONTEXT_MENU_NAVIGATION_LIMIT:
			# Give the raw UIA probe priority. Moving through reaction buttons too
			# quickly makes ReactionsMenuFlyout rebuild its popups and can starve the
			# MTA query behind a continuous focus-event storm.
			pending["navigationScheduled"] = True
			core.callLater(
				_CONTEXT_MENU_NAVIGATION_DELAY_MS,
				self._send_pending_context_menu_navigation_key,
				pending,
			)
		else:
			self.execute_context_menu_option = False
			self.keys["escape"].send()
		return True
	def _send_pending_context_menu_navigation_key(self, pending):
		"""Send one fallback Down only while its original request is active."""
		if self.execute_context_menu_option is not pending or pending.get("rawInvoked"):
			return False
		pending["navigationScheduled"] = False
		self.keys["downArrow"].send()
		return True
	def _schedule_context_menu_raw_probe(self, obj, pending):
		"""Start one persistent probe chain and retain the newest popup root hint."""
		if self.execute_context_menu_option is not pending or pending.get("rawInvoked"):
			return False
		priority = _context_menu_raw_probe_hint_priority(obj)
		if priority >= pending.get("rawProbeObjectPriority", -1):
			pending["rawProbeObject"] = obj
			pending["rawProbeObjectPriority"] = priority
		# Unigram can rebuild its reaction popup several times for one menu. Those
		# focus events can improve the hint without invalidating a queued MTA job.
		if pending["rawProbeToken"]:
			return True
		pending["rawProbeToken"] += 1
		token = pending["rawProbeToken"]
		pending["rawProbeAttempts"] = 0
		pending["rawProbeDiagnosed"] = False
		core.callLater(
			_CONTEXT_MENU_RAW_PROBE_DELAY_MS,
			self._queue_context_menu_raw_probe,
			obj,
			pending,
			token,
		)
		return True
	def _queue_context_menu_raw_probe(self, obj, pending, token):
		"""Run one bounded popup query on NVDA's UIA MTA thread."""
		if (
			self.execute_context_menu_option is not pending
			or pending.get("rawInvoked")
			or pending["rawProbeToken"] != token
			or pending["rawProbeAttempts"] >= _CONTEXT_MENU_RAW_PROBE_LIMIT
		):
			return False
		pending["rawProbeAttempts"] += 1
		try:
			import UIAHandler

			mta_queue = UIAHandler.handler.MTAThreadQueue
		except Exception:
			log.debug("NVDA's UIA MTA queue is unavailable for a context menu", exc_info=True)
			return False

		def probe_on_mta_thread():
			if (
				self.execute_context_menu_option is not pending
				or pending.get("rawInvoked")
				or pending["rawProbeToken"] != token
			):
				return
			probe_hint = pending.get("rawProbeObject") or obj
			probe_roots = []
			try:
				# Prefer UIA's current raw focus. This polling path is started by the
				# shortcut itself, so it survives NVDA coalescing MenuOpened/gainFocus.
				focused_root = _get_raw_context_menu_focus(pending["processID"])
			except Exception:
				log.debug("Could not read Unigram's raw context-menu focus", exc_info=True)
				focused_root = None
			if focused_root:
				probe_roots.append(focused_root)
			# A popup object received from a normal event is independent evidence. A
			# transient focus on Unigram's generic Window must not hide this narrower
			# root, and a provider failure on either root must not skip the other.
			if probe_hint is not None and probe_hint is not focused_root:
				probe_roots.append(probe_hint)
			diagnose = bool(probe_roots) and not pending["rawProbeDiagnosed"]
			if probe_roots:
				pending["rawProbeDiagnosed"] = True
			invoked = False
			for probe_root in probe_roots:
				try:
					invoked = _invoke_raw_context_menu_option(
						probe_root,
						pending["icons"],
						pending["processID"],
						diagnose=diagnose,
					)
				except Exception:
					log.debug("Could not inspect an Unigram context-menu root", exc_info=True)
					continue
				if invoked:
					break
			if invoked:
				# Prevent another already-queued probe from invoking the same command
				# before the main-thread completion callback clears the request.
				pending["rawInvoked"] = True
			queueHandler.queueFunction(
				queueHandler.eventQueue,
				self._complete_context_menu_raw_probe,
				probe_hint,
				pending,
				token,
				invoked,
			)

		try:
			mta_queue.put_nowait(probe_on_mta_thread)
			return True
		except Exception:
			log.debug("Could not queue a raw context-menu probe", exc_info=True)
			return False
	def _complete_context_menu_raw_probe(self, obj, pending, token, invoked):
		"""Complete a popup query without allowing stale callbacks to close a new menu."""
		if self.execute_context_menu_option is not pending:
			return
		if invoked:
			log.debug("Invoked Unigram context-menu command from its raw FontIcon")
			self.execute_context_menu_option = False
			return
		if pending["rawProbeToken"] != token:
			return
		if pending["rawProbeAttempts"] < _CONTEXT_MENU_RAW_PROBE_LIMIT:
			core.callLater(
				_CONTEXT_MENU_RAW_RETRY_DELAY_MS,
				self._queue_context_menu_raw_probe,
				pending.get("rawProbeObject") or obj,
				pending,
				token,
			)
		else:
			if pending.get("rawProbeDiagnosed"):
				log.debug(
					"Unigram context-menu icons %r were not found in the latest raw popup",
					pending["icons"],
				)
			else:
				log.debug(
					"No Unigram popup focus was observed for context-menu icons %r after %d raw polls",
					pending["icons"],
					pending["rawProbeAttempts"],
				)
	def _invoke_context_menu_item(self, item):
		try:
			item.doAction()
		except Exception:
			log.debug("Could not invoke the matched Unigram context-menu item", exc_info=True)
			self.keys["escape"].send()
	def _arm_context_menu_timeout(self, pending, delay_ms):
		pending["timeoutToken"] += 1
		token = pending["timeoutToken"]
		core.callLater(delay_ms, self._expire_context_menu_option, pending, token)
	def _expire_context_menu_option(self, pending, token):
		if self.execute_context_menu_option is pending and pending["timeoutToken"] == token:
			self.execute_context_menu_option = False
			if not pending.get("rawInvoked"):
				self.keys["escape"].send()
	def activate_option_for_menu(self, option, list_name=False):
		if self.execute_context_menu_option: return False
		obj = api.getFocusObject()
		if list_name == "Messages" and not self.is_message_object(obj): return False
		elif list_name == "ChatsList" and not _is_chat_list_item(obj): return False
		elif not list_name and not self.is_message_object(obj) and not _is_chat_list_item(obj): return False
		pending = {
			"icons": option,
			"processID": getattr(obj, "processID", 0),
			"moves": 0,
			"navigationScheduled": False,
			"timeoutToken": 0,
			"rawProbeToken": 0,
			"rawProbeAttempts": 0,
			"rawProbeDiagnosed": False,
			"rawProbeObjectPriority": -1,
			"rawInvoked": False,
		}
		self.execute_context_menu_option = pending
		self._arm_context_menu_timeout(pending, _CONTEXT_MENU_OPEN_TIMEOUT_MS)
		# Unigram builds this menu only after awaiting GetMessageProperties. Start
		# polling raw UIA focus now instead of requiring a later popup focus event,
		# which NVDA may legitimately coalesce with another gainFocus event.
		self._schedule_context_menu_raw_probe(None, pending)
		self.keys["Applications"].send()
		return True
	def script_action_escape_key(self, gesture):
		gesture.send()
		if self.is_exit_from_media:
			lastFocusObject = self.saved_items.get("last focus object")
			if lastFocusObject and lastFocusObject.location:
				lastFocusObject.setFocus()
			self.is_exit_from_media = False

	__gestures = {
		"kb:escape": "action_escape_key",
		"kb:space": "actionMediaInMessage",
	}

	def startDeleteMessage(self, isCompleteDeletion = False, useNativeDelete = False):
		obj = api.getFocusObject()
		isMessage = self.is_message_object(obj)
		isChatListItem = not isMessage and _is_chat_list_item(obj)
		if isMessage or isChatListItem:
			# Unigram's native Delete command is implemented by ChatView for messages.
			# Keep the context-menu fallback for chat rows, where no native Delete
			# handler exists.
			useNativeDelete = useNativeDelete and isMessage
			self.isDelete = {
				"isCompleteDeletion": isCompleteDeletion,
				"elements": [],
				"message": "",
				"list": "",
				"state": 1,
				"nativeDelete": useNativeDelete,
			}
			if isMessage:
				self.isDelete["list"] = "messages"
				if self.isDelete["isCompleteDeletion"]: self.isDelete["message"] = _("Message deleted on both sides")
				else: self.isDelete["message"] = _("Message deleted")
			elif isChatListItem:
				self.isDelete["list"] = "chats"
				if obj.children[1].name == "": self.isDelete["message"] = _("You left the group")
				elif obj.children[1].name == "": self.isDelete["message"] = _("You left the channel")
				elif obj.children[1].name == "" and self.isDelete["isCompleteDeletion"]: self.isDelete["message"] = _("Bot removed and blocked")
				elif obj.children[1].name == "": self.isDelete["message"] = _("Bot removed")
				elif self.isDelete["isCompleteDeletion"]: self.isDelete["message"] = _("Chat deleted on both sides")
				else: self.isDelete["message"] = _("Chat deleted")
			if conf.get("audioPlaybackWhenDeleted"): self.isDelete["message"] = "audio"
			# The native command lets Unigram move focus after deletion. Building an
			# adjacent-item cache here performs extra synchronous UIA calls before the
			# dialog opens and is unnecessary for Shift+Delete.
			if not useNativeDelete:
				if obj.parent.role == Role.LISTITEM: obj = obj.parent
				if obj.next and obj.next.role == Role.LISTITEM and obj.next.childCount > 1: self.isDelete["elements"].append(obj.next.firstChild)
				if obj.previous and obj.previous.role == Role.LISTITEM and obj.previous.childCount > 1: self.isDelete["elements"].append(obj.previous.firstChild)
				if obj.previous and obj.previous.previous and obj.previous.previous.role == Role.LISTITEM and obj.previous.previous.childCount > 1: self.isDelete["elements"].append(obj.previous.previous.firstChild)
				if obj.next and obj.next.next and obj.next.next.role == Role.LISTITEM and obj.next.next.childCount > 1: self.isDelete["elements"].append(obj.next.next.firstChild)
			if not useNativeDelete:
				if conf.get("confirmation_at_deletion"):
					self.isDelete = False
				menuList = "Messages" if isMessage else "ChatsList"
				if not self.activate_option_for_menu(
					(icons_from_context_menu["delete"],), menuList
				):
					self.isDelete = False
					return False
			else:
				self.keys["delete"].send()
			if useNativeDelete and conf.get("confirmation_at_deletion"):
				self.isDelete = False
			elif useNativeDelete:
				core.callLater(20000, self._expire_native_delete, self.isDelete)
			return True
		else: return False


	def fixedDoAction(self, obj):
		p = obj.location.center
		oldX, oldY = winUser.getCursorPos()
		winUser.setCursorPos(p.x, p.y)
		mouseHandler.executeMouseEvent(winUser.MOUSEEVENTF_LEFTDOWN, 0, 0)
		mouseHandler.executeMouseEvent(winUser.MOUSEEVENTF_LEFTUP, 0, 0)
		winUser.setCursorPos(oldX, oldY)

	def change_chats_folder(self, obj, parent):
		selected_folder = self._get_chat_folder_name(obj.name)
		last_selected_folder = self.saved_items.get("last selected folder")
		if last_selected_folder != selected_folder:
			self.saved_items.save("last selected folder", selected_folder)
		else: return False
		text = self.saved_items.get("last selected folder")
		queueHandler.queueFunction(queueHandler.eventQueue, message, text)

	def _get_chat_folder_name(self, name):
		name = str(name or "").strip()
		if name.startswith("(") and name.endswith(")"):
			name = name[1:-1].strip()
		name = name.split(", ")[0].strip()
		name = re.sub(r"\s+\d+$", "", name).strip()
		return name

	# Data copy function for broadcasting
	@script(description=_("Copy data for broadcasting to the clipboard"), gesture="kb:ALT+shift+L")
	def script_copy_data_for_broadcast(self, gesture):
		dialog = next((item for item in self.getElements() if item.role == Role.DIALOG), False)
		if not dialog:
			message(_("Broadcast window not found"))
			return False
		data_area = next((item for item in dialog.children if item.role == Role.PANE and item.UIAAutomationId == "ContentScrollViewer"), False)
		if not data_area:
			message(_("Broadcast window not found"))
			return False
		url = next((item for item in data_area.children if item.UIAAutomationId == "Presenter"), False)
		key = url.next.next
		result_message = f"{url.previous.name}: {url.name}\n{key.previous.name}: {key.name}"
		api.copyToClip(result_message.strip())
		text_message = _("%url and %key copied to clipboard")
		text_message = text_message.replace("%url", url.previous.name)
		text_message = text_message.replace("%key", key.previous.name)
		message(text_message)


	def _is_visible_playback_slider(self, obj):
		try:
			location = obj.location
			return bool(
				obj.UIAAutomationId == "Slider"
				and (obj.name == "Seek" or obj.role == Role.SLIDER)
				and location
				and location.width > 0
			)
		except Exception:
			# UIA objects become stale whenever Unigram rebuilds the playback header.
			return False

	def _get_playback_slider(self):
		slider = self.saved_items.get("slider")
		if self._is_visible_playback_slider(slider):
			return slider
		queue_list = [(candidate, 0) for candidate in self.getElements()]
		visited = set()
		while queue_list and len(visited) < 500:
			candidate, depth = queue_list.pop(0)
			candidate_id = id(candidate)
			if candidate_id in visited:
				continue
			visited.add(candidate_id)
			if not self._is_visible_playback_slider(candidate):
				if depth >= 12:
					continue
				try:
					children = tuple(candidate.children or ())
				except Exception:
					children = ()
				try:
					child = candidate.firstChild
					while child:
						children += (child,)
						child = child.next
				except Exception:
					pass
				queue_list.extend((child, depth + 1) for child in children)
				continue
			self.saved_items.save("slider", candidate)
			return candidate
		return None

	def rewind_voice_message(self, direction):
		slider = self._get_playback_slider()
		if not slider:
			message(_("Nothing is playing right now"))
			return False
		obj = api.getFocusObject()
		succeeded = False
		try:
			slider.setFocus()
			KeyboardInputGesture.fromName(direction).send()
			succeeded = True
		except Exception as error:
			log.debug("Could not seek Unigram voice-message playback: %r" % error)
		finally:
			if obj:
				try:
					obj.setFocus()
				except Exception:
					pass
		if not succeeded:
			message(_("Nothing is playing right now"))
			return False
		speech.cancelSpeech()
		if obj:
			try:
				obj.setFocus()
			except Exception:
				pass
		return True

	def script_rewind_voice_message(self, gesture):
		try: index = int(gesture.mainKeyName[-1])
		except (AttributeError, ValueError): return
		slider = self._get_playback_slider()
		if not slider:
			message(_("Nothing is playing right now"))
			return False
		obj = api.getFocusObject()
		part = slider.location.width // 10
		x = slider.location.left + (part * index)
		y = slider.location.top + (slider.location.height // 2)
		winUser.setCursorPos(x, y)
		mouseHandler.executeMouseEvent(winUser.MOUSEEVENTF_LEFTDOWN, 0, 0)
		mouseHandler.executeMouseEvent(winUser.MOUSEEVENTF_LEFTUP, 0, 0)
	
	
	@script(description=_("Fast forward a voice message"), gesture="kb:control+ALT+rightArrow")	
	def script_rewindVoiceMessageForward(self, gesture):
		self.rewind_voice_message("rightArrow")

	@script(description=_("Rewind voice message"), gesture="kb:control+ALT+leftArrow")
	def script_rewindVoiceMessageBack(self, gesture):
		self.rewind_voice_message("leftArrow")

	def script_set_reaction(self, gesture):
		obj = api.getFocusObject()
		if not self.is_message_object(obj): return
		# p = obj.location.center
		# winUser.setCursorPos(p.x, p.y)
		# mouseHandler.executeMouseEvent(winUser.MOUSEEVENTF_RIGHTDOWN, 0, 0)
		# mouseHandler.executeMouseEvent(winUser.MOUSEEVENTF_RIGHTUP, 0, 0)
		self.keys["Applications"].send()
		try: index = int(gesture.mainKeyName[-1])
		except (AttributeError, ValueError): return
		self.is_set_reaction = index


	def processing_of_answer_options_in_surveys(self, obj):
		tmp_el = obj.firstChild
		processing_of_answer_options_in_surveys = False # Checking the correctness of the answer in the vote
		while tmp_el.next: # Going through the elements, checking if this option is the correct answer in the vote
			tmp_el = tmp_el.next
			if tmp_el.name == "\uf13e": processing_of_answer_options_in_surveys = True
		_("Right answer") # This is necessary for this phrase to appear in the translation dictionary
		return f'{_("Right answer")+": " if processing_of_answer_options_in_surveys else ""}{obj.name}, '


	# A timer that checks if the voice message has been converted to text
	def waiting_for_recognition(self, obj):
		interval = .5
		def tick(obj):
			if not obj or not obj.next: return
			if obj.next.UIAAutomationId == "RecognizedText" and obj.next.name:
				def speak_result():
					if obj and obj.next: text = obj.next.name
					else: text = ""
					queueHandler.queueFunction(queueHandler.eventQueue, message, text)
				Timer(.4, speak_result).start()
				try: playWaveFile(baseDir+"RecognitionFinish.wav")
				except: pass
				return
			else: 
				Timer(interval, tick, [obj]).start()
		Timer(interval, tick, [obj]).start()

	# Converting voice messages to text
	@script(description=_("Convert voice message to text"), gesture="kb:NVDA+ALT+R")
	def script_Recognize_voice_message(self, gesture):
		obj = api.getFocusObject()
		button = next((item for item in obj.children if item.UIAAutomationId == "Recognize"), None)
		if button:
			# if button.next and button.next.UIAAutomationId == "RecognizedText":
			if State.PRESSED in button.states or button.next and button.next.UIAAutomationId == "RecognizedText":
				if button.next.UIAAutomationId == "RecognizedText" and button.next.name: message(_("This voice message is already converted to text"))
				elif button.next.UIAAutomationId == "RecognizedText" and button.next.name == "": message(_("Converting this voice message is already in process"))
				return
			button.doAction()
			obj.setFocus()
			try: playWaveFile(baseDir+"RecognitionStart.wav")
			except: message("Conversion started")
			self.waiting_for_recognition(button)
		else: message(_("Button not found"))


	@script(description=_("Enable automatic reading of new messages in the current chat"), gesture="kb:ALT+L")
	def script_toggle_live_chat(self, gesture):
		if Chat_update.toggle(self): message(_("Automatic reading of messages is enabled"))
		else: message(_("Automatic reading of new messages is disabled"))

	# Translators: Input gesture description for Alt+[ (or Alt+Х on a Russian layout).
	@script(
		description=_("Toggle whether message headers are announced before or after the message content"),
		gestures=["kb:ALT+[", "kb:ALT+Х"],
	)
	def script_toggleMessageHeaderAtTheEnd(self, gesture):
		enabled = not conf.get("messageHeaderAtTheEnd")
		conf.set("messageHeaderAtTheEnd", enabled)
		if enabled:
			message(_("Message headers will be announced after the message content"))
		else:
			message(_("Message headers will be announced before the message content"))
		return enabled

	# Translators: Input gesture description for NVDA+Alt+V in Unigram.
	@script(
		description=_("Announce the Unigram and UnigramPlus version numbers"),
		gesture="kb:NVDA+alt+V",
	)
	def script_announceVersions(self, gesture):
		try:
			cached_version = getattr(self, "app_version", None)
			unigram_version = str(cached_version).strip() if cached_version is not None else ""
		except Exception:
			unigram_version = ""
		if not unigram_version:
			try:
				product_version = self.productVersion
				unigram_version = str(product_version).strip() if product_version is not None else ""
			except Exception:
				unigram_version = ""
		try:
			manifest_version = addonHandler.getCodeAddon().manifest["version"]
			addon_version = str(manifest_version).strip() if manifest_version is not None else ""
		except Exception:
			addon_version = ""
		# Translators: Reported when NVDA+Alt+V is pressed in Unigram. Keep the
		# content inside braces unchanged; it is replaced with each installed version.
		message(
			_("Unigram version: {unigramVersion}. UnigramPlus version: {addonVersion}.").format(
				unigramVersion=unigram_version or "-",
				addonVersion=addon_version or "-",
			)
		)
	
	@script(description=_("Show a list of all UnigramPlus shortcuts"), gesture="kb:ALT+H")
	def script_help(self, gesture):
		a = next((item for item in list(addonHandler.getAvailableAddons()) if item.name == "unigramPlus"), None)
		a = a.getDocFilePath()
		# We replace the file extension, because we need an md file
		a = a[:-4]+"md"
		with open(a, "r", encoding="utf-8") as file:
			text = extractShortcutText(file.read())
		TextWindow(text.strip(), _("List of shortcuts"), readOnly=True)

	@script(description=_("Go to the list with search results"), gesture="kb:ALT+I")
	def script_go_to_list_search_results(self, gesture):
		# Older Unigram versions exposed the result counter as a button. Current
		# versions expose a ListAutocomplete through the search field's UIA
		# ControllerFor relation. The list is collapsed until the field receives
		# focus, so its location and sibling position cannot be used to find it.
		elements = tuple(self.getElements())
		found_search_field = False
		for field in elements:
			try:
				if field.UIAAutomationId != "Field":
					continue
				location = field.location
				if location and (location.width <= 0 or location.height <= 0):
					continue
			except Exception:
				continue
			found_search_field = True
			try:
				controlled = tuple(field.controllerFor or ())
			except Exception:
				controlled = ()
			results_list = next((item for item in controlled
				if getattr(item, "UIAAutomationId", "") == "ListAutocomplete"), None)
			if results_list is None:
				# Some older UIA providers omit ControllerFor. Keep a bounded local
				# sibling fallback and a flat-tree fallback for those versions.
				results_list = next((item for item in elements
					if getattr(item, "UIAAutomationId", "") == "ListAutocomplete"), None)
			counter = field
			count = None
			for _step in range(_SEARCH_RESULT_COUNTER_SIBLING_LIMIT):
				try:
					counter = counter.next
				except Exception:
					counter = None
				if not counter:
					break
				count = _parse_search_result_counter(counter)
				if count is None:
					continue
				try:
					role = counter.role
				except Exception:
					role = None
				if role == Role.BUTTON:
					try:
						counter.doAction()
						return True
					except Exception:
						break
				if count[1] <= 0:
					message(_("No search results"))
					return False
				break
			if results_list is not None or count is not None:
				try:
					field.setFocus()
				except Exception:
					continue
				queueHandler.queueFunction(
					queueHandler.eventQueue,
					self.keys["downArrow"].send,
				)
				return True
		message(_("No search results") if found_search_field else _("Button not found"))
		return False

	def _profile_media_content_anchor(self, obj):
		"""Return a content anchor for a profile media row, or ``None`` otherwise."""
		try:
			if obj.parent.UIAAutomationId != "ScrollingHost":
				return None
		except Exception:
			return None
		inside_profile_context = False
		ancestor = obj.parent
		for _depth in range(10):
			if not ancestor:
				break
			try:
				class_name = str(getattr(ancestor, "UIAClassName", "") or "").casefold()
				automation_id = str(getattr(ancestor, "UIAAutomationId", "") or "").casefold()
				if "profile" in class_name or automation_id in ("profile", "profilepage"):
					inside_profile_context = True
				parent = ancestor.parent
			except Exception:
				break
			if not parent or parent is ancestor:
				break
			ancestor = parent
		if not inside_profile_context:
			# RussianMod's working profile-media signature follows the UIA control
			# tree exposed by NVDA: a Title in the surrounding profile tab and a
			# VerticalScrollBar immediately after its ScrollingHost. XAML Page class
			# names are not exposed as UIA ancestors on every Unigram/NVDA version.
			try:
				tab_title = obj.parent.parent.firstChild.next.next
				scrollbar = obj.parent.next
				inside_profile_context = (
					tab_title.UIAAutomationId == "Title"
					and scrollbar.UIAAutomationId == "VerticalScrollBar"
				)
			except Exception:
				pass
		if not inside_profile_context:
			return None
		title = self._find_descendant(obj, automation_id="Title", max_depth=5)
		# Require the distinctive shared file/audio cell signature even inside a
		# profile page. MediaFrame is also used by unrelated search and settings UI.
		subtitle = self._find_descendant(obj, automation_id="Subtitle", max_depth=5)
		file_button = self._find_descendant(
			obj, automation_id="Download", max_depth=5
		) or self._find_descendant(obj, automation_id="Button", max_depth=5)
		if not title or not subtitle or not file_button:
			return None
		try:
			return title.name or "" if title else ""
		except Exception:
			return ""
	
	@script(description=_("Go to the next search result"), gesture="kb:F3")
	def script_go_to_previous_search_result(self, gesture):
		obj = api.getFocusObject()
		btn = next((element for element in self.getElements()
			if element.UIAAutomationId == "SearchPrevious"and element.role == Role.BUTTON), None)
		if btn and State.FOCUSABLE in btn.states: btn.doAction()
		elif btn: message(_("No next search result"))
		else: message(_("Button not found"))
	
	@script(description=_("Go to the previous search result"), gesture="kb:shift+F3")
	def script_go_to_next_search_result(self, gesture):
		obj = api.getFocusObject()
		btn = next((element for element in self.getElements()
			if element.UIAAutomationId == "SearchNext"and element.role == Role.BUTTON), None)
		if btn and State.FOCUSABLE in btn.states: btn.doAction()
		elif btn: message(_("No previous search result"))
		else: message(_("Button not found"))


def is_version_greater(v1, v2):
    parts1 = list(map(int, v1.split('.')))
    parts2 = list(map(int, v2.split('.')))
    
    # Equal the length of two lists by adding zero
    length = max(len(parts1), len(parts2))
    parts1 += [0] * (length - len(parts1))
    parts2 += [0] * (length - len(parts2))
    
    for p1, p2 in zip(parts1, parts2):
        if p1 > p2:
            return True
        elif p1 < p2:
            return False
    return False  # Equality
