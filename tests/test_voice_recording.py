import ast
from pathlib import Path
import sys
from types import SimpleNamespace


ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "addon" / "appModules"))

from voice_recording import (  # noqa: E402
	VoiceRecordingOutcome,
	VoiceRecordingState,
	is_recorded_message,
	is_recording_button,
	message_marker,
	recording_button_state,
)


def _app_module_ast():
	source = (ROOT / "addon" / "appModules" / "unigram.py").read_text(encoding="utf-8")
	module = ast.parse(source)
	return next(node for node in module.body if isinstance(node, ast.ClassDef) and node.name == "AppModule")


def _load_method(name, namespace):
	method = next(
		node
		for node in _app_module_ast().body
		if isinstance(node, ast.FunctionDef) and node.name == name
	)
	method.decorator_list = []
	exec(compile(ast.Module(body=[method], type_ignores=[]), "unigram.py", "exec"), namespace)
	return namespace[name]


def test_native_recording_shortcuts_are_not_bound_or_intercepted_by_unigramplus():
	app_module = _app_module_ast()
	legacy_scripts = {
		"script_recordingVoiceMessage",
		"script_cancelVoiceMessageRecording",
	}
	recording_scripts = {
		node.name
		for node in app_module.body
		if isinstance(node, ast.FunctionDef) and node.name in legacy_scripts
	}
	serialized = ast.dump(app_module).casefold()

	assert recording_scripts == set()
	assert "control+r" not in serialized
	assert "control+d" not in serialized


def test_native_recording_ui_events_produce_one_start_and_one_stop():
	state = VoiceRecordingState()

	assert state.shown() == "start"
	assert state.elapsedChanged("0:00,00") is None
	assert state.elapsedChanged("0:00.10") is None
	assert state.elapsedChanged("0:01.25") is None
	assert state.elapsedChanged("0:00,0") == "stopped"
	assert state.hidden() is None
	assert state.elapsedChanged("0:00,0") is None


def test_name_changes_work_when_uia_show_event_is_missing():
	state = VoiceRecordingState()

	assert state.elapsedChanged("0:00.10") == "start"
	assert state.elapsedChanged("0:00.00") == "stopped"


def test_hiding_timer_defers_the_send_or_cancel_outcome():
	state = VoiceRecordingState()

	assert state.shown() == "start"
	assert state.elapsedChanged("0:01.25") is None
	assert state.hidden() == "stopped"
	assert not state.active


def test_recorded_message_templates_and_message_markers_are_detected():
	voice = SimpleNamespace(
		UIAAutomationId="Message_item",
		children=[SimpleNamespace(UIAAutomationId="Recognize", children=[])],
	)
	voice_without_transcription = SimpleNamespace(
		UIAAutomationId="Message_item",
		children=[SimpleNamespace(UIAAutomationId="Subtitle", name="00:00 / 00:03", children=[])],
	)
	video = SimpleNamespace(
		UIAAutomationId="Message_item",
		children=[
			SimpleNamespace(UIAAutomationId="Player", children=[]),
			SimpleNamespace(UIAAutomationId="Subtitle", children=[]),
		],
	)
	text = SimpleNamespace(UIAAutomationId="Message_item", children=[])
	positioned = SimpleNamespace(positionInfo={"indexInGroup": 12, "similarItemsInGroup": 12})
	recycled_position = SimpleNamespace(positionInfo={"indexInGroup": 12, "similarItemsInGroup": 13})

	assert is_recorded_message(voice)
	assert is_recorded_message(voice_without_transcription)
	assert not is_recorded_message(text)
	assert is_recorded_message(video, video=True)
	assert not is_recorded_message(voice, video=True)
	assert message_marker(positioned) == ("position", 12, 12)
	assert message_marker(recycled_position) != message_marker(positioned)


def test_stopped_recording_is_sent_only_after_a_new_recorded_message_appears():
	outcome = VoiceRecordingOutcome(poll_limit=3)
	outcome.started(("position", 8))
	outcome.stopped()

	assert outcome.observe(("position", 8), is_recorded=True) is None
	assert outcome.observe(("position", 9), is_recorded=False) is None
	assert outcome.observe(("position", 9), is_recorded=True) == "sent"
	assert not outcome.pending


def test_new_message_is_sent_when_unigram_delays_its_voice_controls():
	outcome = VoiceRecordingOutcome(poll_limit=4)
	outcome.started(("position", 8, 8))
	outcome.stopped()

	assert outcome.observe(("position", 9, 9), is_recorded=False) is None
	assert outcome.observe(("position", 9, 9), is_recorded=False) == "sent"
	assert not outcome.pending


def test_transient_message_list_read_failure_is_not_treated_as_sent():
	outcome = VoiceRecordingOutcome(poll_limit=3)
	outcome.started(("position", 8, 8))
	outcome.stopped()

	assert outcome.observe(None, is_recorded=False) is None
	assert outcome.observe(("position", 8, 8), is_recorded=False) is None
	assert outcome.observe(("position", 8, 8), is_recorded=False) == "canceled"


def test_stopped_recording_without_a_new_recorded_message_is_canceled():
	outcome = VoiceRecordingOutcome(poll_limit=2)
	outcome.started(("position", 8))
	outcome.stopped()

	assert outcome.observe(("position", 8), is_recorded=False) is None
	assert outcome.observe(("position", 8), is_recorded=False) == "canceled"
	assert not outcome.pending


def test_default_outcome_window_allows_slow_recording_finalization():
	outcome = VoiceRecordingOutcome(poll_limit=25)
	outcome.started(("position", 8))
	outcome.stopped()

	for _ in range(24):
		assert outcome.observe(("position", 8), is_recorded=False) is None
	assert outcome.observe(("position", 8), is_recorded=False) == "canceled"


def test_recording_state_uses_the_same_elapsed_sibling_as_the_button_label():
	idle_button = SimpleNamespace(
		UIAAutomationId="btnVoiceMessage",
		next=SimpleNamespace(UIAAutomationId="SomeOtherControl"),
	)
	recording_button = SimpleNamespace(
		UIAAutomationId="btnVoiceMessage",
		next=SimpleNamespace(UIAAutomationId="ElapsedLabel"),
	)

	assert is_recording_button(idle_button)
	assert recording_button_state(idle_button) is False
	assert recording_button_state(recording_button) is True
	assert recording_button_state(SimpleNamespace(UIAAutomationId="SendButton")) is None


def test_unreadable_cached_button_is_rediscovered_instead_of_misdetected():
	class StaleButton:
		UIAAutomationId = "btnVoiceMessage"

		@property
		def next(self):
			raise RuntimeError("stale UIA object")

	assert recording_button_state(StaleButton()) is None


def test_cached_recording_button_avoids_repeated_ui_tree_searches():
	button = SimpleNamespace(UIAAutomationId="btnVoiceMessage")
	focus = SimpleNamespace(UIAAutomationId="TextField")
	instance = SimpleNamespace(
		_voiceRecordingButton=button,
		_voiceRecordingDiscoveryFocus=None,
		getElements=lambda: (_ for _ in ()).throw(AssertionError("unexpected UI tree scan")),
	)
	namespace = {"is_recording_button": is_recording_button}
	method = _load_method("_getVoiceRecordingButton", namespace)

	assert method(instance, focus) is button


def test_recording_button_discovery_runs_only_once_for_the_same_focus():
	focus = SimpleNamespace(UIAAutomationId="TextField")
	searches = []
	instance = SimpleNamespace(
		_voiceRecordingButton=None,
		_voiceRecordingDiscoveryFocus=None,
		getElements=lambda: searches.append(True) or [],
	)
	namespace = {"is_recording_button": is_recording_button}
	method = _load_method("_getVoiceRecordingButton", namespace)

	assert method(instance, focus) is None
	assert method(instance, focus) is None
	assert searches == [True]


def test_recording_monitor_schedules_on_nvda_main_loop_without_timer_threads(monkeypatch):
	scheduled = []
	core = SimpleNamespace(callLater=lambda delay, callback: scheduled.append((delay, callback)))
	monkeypatch.setitem(sys.modules, "core", core)
	instance = SimpleNamespace(
		_voiceRecordingMonitorRunning=True,
		_pollVoiceRecordingState=lambda: None,
	)
	namespace = {"_VOICE_RECORDING_POLL_INTERVAL": 0.2}
	method = _load_method("_scheduleVoiceRecordingPoll", namespace)

	method(instance)

	assert scheduled == [(200, instance._pollVoiceRecordingState)]


def test_app_transition_handler_captures_baseline_before_resolving_outcome():
	announcements = []
	button = SimpleNamespace(states=set())
	outcome = VoiceRecordingOutcome(poll_limit=2)
	instance = SimpleNamespace(
		_voiceRecordingButton=button,
		_voiceRecordingOutcome=outcome,
		_getVoiceRecordingLastMessage=lambda: (("position", 5), object()),
		_announceVoiceRecordingTransition=announcements.append,
	)
	namespace = {"State": SimpleNamespace(PRESSED="pressed")}
	method = _load_method("_handleVoiceRecordingTransition", namespace)

	method(instance, "start")
	method(instance, "stopped")

	assert outcome.baseline == ("position", 5)
	assert outcome.pending
	assert not outcome.video
	assert announcements == ["start"]


def test_app_outcome_poll_announces_new_voice_message_as_sent():
	announcements = []
	logs = []
	voice = SimpleNamespace(
		UIAAutomationId="Message_item",
		children=[SimpleNamespace(UIAAutomationId="Recognize", children=[])],
	)
	outcome = VoiceRecordingOutcome(poll_limit=2)
	outcome.started(("position", 5))
	outcome.stopped()
	instance = SimpleNamespace(
		_voiceRecordingOutcome=outcome,
		_getVoiceRecordingLastMessage=lambda: (("position", 6), voice),
		_announceVoiceRecordingTransition=announcements.append,
	)
	namespace = {
		"is_recorded_message": is_recorded_message,
		"log": SimpleNamespace(info=logs.append),
	}
	method = _load_method("_pollVoiceRecordingOutcome", namespace)

	method(instance)

	assert announcements == ["sent"]
	assert logs and logs[0].endswith("sent")
	assert not outcome.pending


def test_polling_native_ui_announces_manual_or_keyboard_recording_once():
	transitions = []
	scheduled = []

	button = SimpleNamespace(
		UIAAutomationId="btnVoiceMessage",
		next=SimpleNamespace(UIAAutomationId="ElapsedLabel"),
	)
	instance = SimpleNamespace(
		_voiceRecordingMonitorRunning=True,
		_voiceRecordingState=VoiceRecordingState(),
		_voiceRecordingButton=button,
		_getVoiceRecordingButton=lambda focus: button,
		_pollVoiceRecordingOutcome=lambda: None,
		_handleVoiceRecordingTransition=lambda transition: transitions.append(transition) if transition else None,
		_scheduleVoiceRecordingPoll=lambda: scheduled.append(True),
	)
	focus = SimpleNamespace(appModule=instance)
	namespace = {
		"api": SimpleNamespace(getFocusObject=lambda: focus),
		"recording_button_state": recording_button_state,
		"log": SimpleNamespace(debug=lambda text: None, info=lambda text: None),
	}
	method = _load_method("_pollVoiceRecordingState", namespace)

	method(instance)
	method(instance)
	button.next = SimpleNamespace(UIAAutomationId="SomeOtherControl")
	method(instance)

	assert transitions == ["start", "stopped"]
	assert scheduled == [True, True, True]
	assert not instance._voiceRecordingState.active


def test_recording_transitions_keep_text_and_audio_notifications():
	announcements = []
	sounds = []
	button = SimpleNamespace(
		role="toggle",
		UIAAutomationId="btnVoiceMessage",
		states=set(),
	)
	settings = {"indicator": "text"}
	namespace = {
		"conf": SimpleNamespace(get=lambda key: settings["indicator"]),
		"Role": SimpleNamespace(TOGGLEBUTTON="toggle"),
		"State": SimpleNamespace(PRESSED="pressed"),
		"winsound": SimpleNamespace(
			SND_ASYNC=1,
			SND_NOSTOP=2,
			PlaySound=lambda path, flags: sounds.append((path, flags)),
		),
		"baseDir": "media/",
		"message": announcements.append,
		"log": SimpleNamespace(debug=lambda text: None),
		"_": lambda text: text,
	}
	method = _load_method("_announceVoiceRecordingTransition", namespace)
	instance = SimpleNamespace(_voiceRecordingButton=button)

	method(instance, "start")
	method(instance, "sent")
	method(instance, "canceled")
	settings["indicator"] = "audio"
	method(instance, "start")
	method(instance, "sent")
	method(instance, "canceled")

	assert announcements == ["Audio", "Record sent", "Recording canceled"]
	assert sounds[0][0].endswith("start_recording_voice_message.wav")
	assert sounds[1][0].endswith("send_voice_message.wav")
	assert sounds[2][0].endswith("cancel_voice_message_recording.wav")
