"""State transitions for Unigram's native voice/video recording UI."""


def _is_zero_elapsed_label(value):
	digits = "".join(character for character in str(value or "") if character.isdigit())
	return bool(digits) and not any(character != "0" for character in digits)


class VoiceRecordingState:
	"""Convert UIA show/name/hide events into stable recording transitions."""

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
			self.active = True
			self._seenProgress = not _is_zero_elapsed_label(value)
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

	def _finish(self):
		self.active = False
		self._seenProgress = False
		return "end"
