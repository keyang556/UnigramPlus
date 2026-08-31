import ast
from pathlib import Path
import sys
from types import SimpleNamespace


ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "addon" / "appModules"))

from voice_recording import (  # noqa: E402
	VoiceRecordingOutcome,
	VoiceRecordingState,
	is_elapsed_label,
	is_recorded_message,
	is_recording_button,
	message_marker,
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


def test_recording_outcome_poll_schedules_only_while_an_outcome_is_pending(monkeypatch):
	scheduled = []
	core = SimpleNamespace(callLater=lambda delay, callback: scheduled.append((delay, callback)))
	monkeypatch.setitem(sys.modules, "core", core)
	instance = SimpleNamespace(
		_voiceRecordingOutcomePollingEnabled=True,
		_voiceRecordingOutcome=SimpleNamespace(pending=True),
		_voiceRecordingOutcomePollScheduled=False,
		_pollVoiceRecordingOutcome=lambda: None,
	)
	namespace = {"_VOICE_RECORDING_OUTCOME_POLL_INTERVAL": 0.2}
	method = _load_method("_scheduleVoiceRecordingOutcomePoll", namespace)

	method(instance)
	method(instance)

	assert scheduled == [(200, instance._pollVoiceRecordingOutcome)]
	assert instance._voiceRecordingOutcomePollScheduled


def test_app_module_has_no_permanent_recording_state_poll_or_tree_discovery():
	serialized = ast.dump(_app_module_ast())

	assert "_pollVoiceRecordingState" not in serialized
	assert "_getVoiceRecordingButton" not in serialized
	assert "_voiceRecordingDiscoveryFocus" not in serialized


def test_app_transition_handler_captures_baseline_before_resolving_outcome():
	announcements = []
	scheduled = []
	button = SimpleNamespace(states=set())
	outcome = VoiceRecordingOutcome(poll_limit=2)
	instance = SimpleNamespace(
		_voiceRecordingButton=button,
		_voiceRecordingOutcome=outcome,
		_getVoiceRecordingLastMessage=lambda: (("position", 5), object()),
		_announceVoiceRecordingTransition=announcements.append,
		_scheduleVoiceRecordingOutcomePoll=lambda: scheduled.append(True),
	)
	namespace = {"State": SimpleNamespace(PRESSED="pressed")}
	method = _load_method("_handleVoiceRecordingTransition", namespace)

	method(instance, "start")
	method(instance, "stopped")

	assert outcome.baseline == ("position", 5)
	assert outcome.pending
	assert not outcome.video
	assert announcements == ["start"]
	assert scheduled == [True]


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
		_voiceRecordingOutcomePollingEnabled=True,
		_voiceRecordingOutcome=outcome,
		_voiceRecordingOutcomePollScheduled=True,
		_getVoiceRecordingLastMessage=lambda: (("position", 6), voice),
		_announceVoiceRecordingTransition=announcements.append,
		_scheduleVoiceRecordingOutcomePoll=lambda: (_ for _ in ()).throw(
			AssertionError("a completed outcome must not be rescheduled")
		),
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
	assert not instance._voiceRecordingOutcomePollScheduled


def test_native_elapsed_label_events_announce_recording_once():
	transitions = []
	next_calls = []
	instance = SimpleNamespace(
		isUnigramWindow=True,
		_voiceRecordingState=VoiceRecordingState(),
		_voiceRecordingElapsed="",
		_remember_messages_button=lambda obj: None,
		_handleVoiceRecordingTransition=lambda transition: transitions.append(transition) if transition else None,
	)
	label = SimpleNamespace(UIAAutomationId="ElapsedLabel", name="0:00,00")
	show = _load_method(
		"event_show",
		{"is_recording_button": is_recording_button, "is_elapsed_label": is_elapsed_label},
	)
	name_change = _load_method("event_nameChange", {"is_elapsed_label": is_elapsed_label})
	hide = _load_method(
		"event_hide",
		{"is_recording_button": is_recording_button, "is_elapsed_label": is_elapsed_label},
	)

	show(instance, label, lambda: next_calls.append("show"))
	label.name = "0:00.10"
	name_change(instance, label, lambda: next_calls.append("name"))
	label.name = "0:00,0"
	name_change(instance, label, lambda: next_calls.append("name"))
	hide(instance, label, lambda: next_calls.append("hide"))

	assert transitions == ["start", "stopped"]
	assert next_calls == ["show", "name", "name", "hide"]
	assert not instance._voiceRecordingState.active
	assert instance._voiceRecordingElapsed == ""


def test_pending_outcome_reschedules_without_a_permanent_state_monitor():
	scheduled = []
	outcome = VoiceRecordingOutcome(poll_limit=2)
	outcome.started(("position", 5))
	outcome.stopped()
	instance = SimpleNamespace(
		_voiceRecordingOutcomePollingEnabled=True,
		_voiceRecordingOutcome=outcome,
		_voiceRecordingOutcomePollScheduled=True,
		_getVoiceRecordingLastMessage=lambda: (("position", 5), object()),
		_announceVoiceRecordingTransition=lambda transition: None,
		_scheduleVoiceRecordingOutcomePoll=lambda: scheduled.append(True),
	)
	namespace = {
		"is_recorded_message": is_recorded_message,
		"log": SimpleNamespace(info=lambda text: None),
	}
	method = _load_method("_pollVoiceRecordingOutcome", namespace)

	method(instance)

	assert scheduled == [True]
	assert not instance._voiceRecordingOutcomePollScheduled


def test_transient_outcome_read_error_keeps_the_bounded_poll_alive():
	scheduled = []
	debug = []
	outcome = VoiceRecordingOutcome(poll_limit=2)
	outcome.started(("position", 5))
	outcome.stopped()
	instance = SimpleNamespace(
		_voiceRecordingOutcomePollingEnabled=True,
		_voiceRecordingOutcome=outcome,
		_voiceRecordingOutcomePollScheduled=True,
		_getVoiceRecordingLastMessage=lambda: (_ for _ in ()).throw(RuntimeError("stale UIA")),
		_scheduleVoiceRecordingOutcomePoll=lambda: scheduled.append(True),
	)
	namespace = {
		"is_recorded_message": is_recorded_message,
		"log": SimpleNamespace(info=lambda text: None, debug=debug.append),
	}
	method = _load_method("_pollVoiceRecordingOutcome", namespace)

	method(instance)

	assert scheduled == [True]
	assert debug and "stale UIA" in debug[0]
	assert outcome.pending


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
