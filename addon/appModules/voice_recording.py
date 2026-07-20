"""State transitions for Unigram's native voice/video recording UI."""


RECORDING_BUTTON_AUTOMATION_ID = "btnVoiceMessage"
ELAPSED_LABEL_AUTOMATION_ID = "ElapsedLabel"


def _is_zero_elapsed_label(value):
	digits = "".join(character for character in str(value or "") if character.isdigit())
	return bool(digits) and not any(character != "0" for character in digits)


def is_recording_button(obj):
	try:
		return obj.UIAAutomationId == RECORDING_BUTTON_AUTOMATION_ID
	except Exception:
		return False


def recording_button_state(button):
	"""Return True while UnigramPlus can see the button's elapsed-time sibling.

	The same relationship is used when UnigramPlus labels the focused record
	button as "Recording ..., elapsed time". None means that the cached button
	is no longer readable and must be rediscovered.
	"""
	if not is_recording_button(button):
		return None
	try:
		next_element = button.next
	except Exception:
		return None
	try:
		return bool(next_element and next_element.UIAAutomationId == ELAPSED_LABEL_AUTOMATION_ID)
	except Exception:
		return None


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
