import ast
from pathlib import Path
import sys
from types import SimpleNamespace


ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "addon" / "appModules"))

from voice_recording import (  # noqa: E402
	VoiceRecordingState,
	is_recording_button,
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


def test_native_recording_ui_events_produce_one_start_and_one_end():
	state = VoiceRecordingState()

	assert state.shown() == "start"
	assert state.elapsedChanged("0:00,00") is None
	assert state.elapsedChanged("0:00.10") is None
	assert state.elapsedChanged("0:01.25") is None
	assert state.elapsedChanged("0:00,0") == "end"
	assert state.hidden() is None
	assert state.elapsedChanged("0:00,0") is None


def test_name_changes_work_when_uia_show_event_is_missing():
	state = VoiceRecordingState()

	assert state.elapsedChanged("0:00.10") == "start"
	assert state.elapsedChanged("0:00.00") == "end"


def test_hiding_timer_after_native_cancel_does_not_announce_message_sent():
	state = VoiceRecordingState()

	assert state.shown() == "start"
	assert state.elapsedChanged("0:01.25") is None
	assert state.hidden() is None
	assert not state.active


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


def test_polling_native_ui_announces_manual_or_keyboard_recording_once():
	announcements = []
	scheduled = []

	def announce(transition):
		if transition:
			announcements.append(transition)

	button = SimpleNamespace(
		UIAAutomationId="btnVoiceMessage",
		next=SimpleNamespace(UIAAutomationId="ElapsedLabel"),
	)
	instance = SimpleNamespace(
		_voiceRecordingMonitorRunning=True,
		_voiceRecordingState=VoiceRecordingState(),
		_voiceRecordingButton=button,
		_getVoiceRecordingButton=lambda focus: button,
		_announceVoiceRecordingTransition=announce,
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

	assert announcements == ["start"]
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
	method(instance, "end")
	settings["indicator"] = "audio"
	method(instance, "start")
	method(instance, "end")

	assert announcements == ["Audio", "Record sent"]
	assert sounds[0][0].endswith("start_recording_voice_message.wav")
	assert sounds[1][0].endswith("send_voice_message.wav")
