"""State transitions for Unigram's native voice/video recording UI."""


RECORDING_UI_AUTOMATION_IDS = frozenset(("ChatRecord", "ElapsedLabel"))


def _is_zero_elapsed_label(value):
	digits = "".join(character for character in str(value or "") if character.isdigit())
	return bool(digits) and not any(character != "0" for character in digits)


def is_recording_ui_element(obj):
	try:
		return obj.UIAAutomationId in RECORDING_UI_AUTOMATION_IDS
	except Exception:
		return False


def is_recording_ui_visible(elements):
	"""Return whether Unigram's native ChatRecord bar is currently visible."""
	for obj in elements or ():
		if not is_recording_ui_element(obj):
			continue
		try:
			location = obj.location
			if location and location.width > 0 and location.height > 0:
				return True
		except Exception:
			continue
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
