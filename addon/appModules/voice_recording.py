"""State transitions for Unigram's native voice/video recording UI."""


RECORDING_UI_AUTOMATION_IDS = frozenset(("ChatRecord", "ElapsedLabel"))
RECORDING_BUTTON_AUTOMATION_ID = "btnVoiceMessage"


def _is_zero_elapsed_label(value):
	digits = "".join(character for character in str(value or "") if character.isdigit())
	return bool(digits) and not any(character != "0" for character in digits)


def is_recording_ui_element(obj):
	try:
		return obj.UIAAutomationId in RECORDING_UI_AUTOMATION_IDS
	except Exception:
		return False


def is_recording_raw_uia_visible(root_element, client, uia, descendant_scope):
	"""Search the raw UIA tree for a visible native recording control."""
	if root_element is None:
		return False
	id_conditions = [
		client.createPropertyCondition(uia.UIA_AutomationIdPropertyId, automation_id)
		for automation_id in RECORDING_UI_AUTOMATION_IDS
	]
	id_condition = client.createOrConditionFromArray(id_conditions)
	visible_condition = client.createPropertyCondition(uia.UIA_IsOffscreenPropertyId, False)
	condition = client.createAndConditionFromArray([id_condition, visible_condition])
	return root_element.findFirst(descendant_scope, condition) is not None


def is_recording_button_active(root_element, client, uia, descendant_scope):
	"""Read ChatRecordButton's provider name, which is empty only while recording."""
	if root_element is None:
		return False
	id_condition = client.createPropertyCondition(
		uia.UIA_AutomationIdPropertyId,
		RECORDING_BUTTON_AUTOMATION_ID,
	)
	visible_condition = client.createPropertyCondition(uia.UIA_IsOffscreenPropertyId, False)
	condition = client.createAndConditionFromArray([id_condition, visible_condition])
	button = root_element.findFirst(descendant_scope, condition)
	if button is None:
		return False
	try:
		name = button.GetCurrentPropertyValueEx(uia.UIA_NamePropertyId, True)
	except Exception:
		return False
	return not str(name or "").strip()


def get_raw_uia_process_root(element, walker, max_ancestors=64):
	"""Ascend from a UIA element without relying on an HWND or process handle."""
	if element is None:
		return None
	try:
		process_id = element.CurrentProcessId
	except Exception:
		return element
	current = element
	for _ in range(max_ancestors):
		try:
			parent = walker.GetParentElement(current)
			if parent is None or parent.CurrentProcessId != process_id:
				break
		except Exception:
			break
		current = parent
	return current


class VoiceRecordingState:
	"""Convert native recording UI visibility into stable transitions."""

	def __init__(self):
		self.active = False
		self._seenProgress = False

	def shown(self):
		if self.active:
			return None
		self.active = True
		self._seenProgress = False
		return "start"

	def elapsedChanged(self, value):
		if not self.active:
			# Unigram resets the label after collapsing ChatRecord. That terminal
			# zero must not be mistaken for a new recording.
			if _is_zero_elapsed_label(value):
				return None
			self.active = True
			self._seenProgress = True
			return "start"
		if _is_zero_elapsed_label(value):
			# Unigram can emit the initial zero value just after showing the bar.
			# It is an end transition only after the timer has actually advanced.
			return self._finish() if self._seenProgress else None
		self._seenProgress = True
		return None

	def hidden(self):
		if not self.active:
			return None
		# Hiding alone cannot distinguish a native Ctrl+D cancellation from a
		# completed send. Only the elapsed timer returning to zero signals "end".
		self.active = False
		self._seenProgress = False
		return None

	def visibilityChanged(self, visible):
		return self.shown() if visible else self.hidden()

	def _finish(self):
		self.active = False
		self._seenProgress = False
		return "end"
