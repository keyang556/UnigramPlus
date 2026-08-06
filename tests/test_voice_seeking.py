import ast
from pathlib import Path
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = ROOT / "addon" / "appModules" / "unigram.py"


def _app_class_ast():
	module = ast.parse(SOURCE_PATH.read_text(encoding="utf-8"))
	return next(node for node in module.body if isinstance(node, ast.ClassDef) and node.name == "AppModule")


def _load_methods(names, namespace):
	methods = [
		node for node in _app_class_ast().body if isinstance(node, ast.FunctionDef) and node.name in names
	]
	for method in methods:
		method.decorator_list = []
	exec(
		compile(ast.Module(body=methods, type_ignores=[]), str(SOURCE_PATH), "exec"),
		namespace,
	)
	return [namespace[name] for name in names]


class _SavedItems:
	def __init__(self, slider=None):
		self.slider = slider
		self.saved = []

	def get(self, key):
		assert key == "slider"
		return self.slider

	def save(self, key, value):
		assert key == "slider"
		self.slider = value
		self.saved.append(value)


def _slider(width=200, role="unknown", name="Seek"):
	return SimpleNamespace(
		role=role,
		UIAAutomationId="Slider",
		name=name,
		location=SimpleNamespace(width=width),
		setFocus=lambda: None,
	)


def _node(*children):
	return SimpleNamespace(
		role="window",
		UIAAutomationId="Window",
		name="",
		location=SimpleNamespace(width=800),
		children=list(children),
	)


def _load_slider_helpers():
	namespace = {"Role": SimpleNamespace(SLIDER="slider")}
	return _load_methods(
		["_is_visible_playback_slider", "_get_playback_slider"],
		namespace,
	)


def test_current_custom_role_playback_slider_is_discovered_and_cached():
	is_visible, get_slider = _load_slider_helpers()
	current = _slider(role="unknown")
	saved = _SavedItems()
	instance = SimpleNamespace(
		saved_items=saved,
		getElements=lambda: [SimpleNamespace(UIAAutomationId="Other"), current],
		_is_visible_playback_slider=lambda obj: is_visible(None, obj),
	)

	assert get_slider(instance) is current
	assert saved.saved == [current]


def test_hidden_cached_slider_is_replaced_by_the_live_slider():
	is_visible, get_slider = _load_slider_helpers()
	stale = _slider(width=0)
	current = _slider(width=300, role="unknown")
	saved = _SavedItems(stale)
	instance = SimpleNamespace(
		saved_items=saved,
		getElements=lambda: [current],
		_is_visible_playback_slider=lambda obj: is_visible(None, obj),
	)

	assert get_slider(instance) is current
	assert saved.saved == [current]


def test_stale_cached_slider_exception_is_replaced():
	class StaleSlider:
		UIAAutomationId = "Slider"
		name = "Seek"
		role = "unknown"

		@property
		def location(self):
			raise RuntimeError("element no longer available")

	is_visible, get_slider = _load_slider_helpers()
	current = _slider(role="unknown")
	saved = _SavedItems(StaleSlider())
	instance = SimpleNamespace(
		saved_items=saved,
		getElements=lambda: [current],
		_is_visible_playback_slider=lambda obj: is_visible(None, obj),
	)

	assert get_slider(instance) is current
	assert saved.saved == [current]


def test_nested_current_playback_slider_is_discovered():
	is_visible, get_slider = _load_slider_helpers()
	current = _slider(role="unknown")
	saved = _SavedItems()
	instance = SimpleNamespace(
		saved_items=saved,
		getElements=lambda: [_node(_node(current))],
		_is_visible_playback_slider=lambda obj: is_visible(None, obj),
	)

	assert get_slider(instance) is current
	assert saved.saved == [current]


@pytest.mark.parametrize("direction", ["rightArrow", "leftArrow"])
def test_voice_seek_uses_current_slider_and_restores_playback_and_focus(direction):
	events = []
	messages = []
	focus = SimpleNamespace(setFocus=lambda: events.append("restoreFocus"))
	slider = _slider(role="unknown")
	slider.setFocus = lambda: events.append("sliderFocus")

	class Gesture:
		def send(self):
			events.append(direction)

	_, _, rewind = _load_methods(
		["_is_visible_playback_slider", "_get_playback_slider", "rewind_voice_message"],
		{
			"Role": SimpleNamespace(SLIDER="slider"),
			"message": messages.append,
			"_": lambda text: text,
			"api": SimpleNamespace(getFocusObject=lambda: focus),
			"KeyboardInputGesture": SimpleNamespace(fromName=lambda name: Gesture()),
			"speech": SimpleNamespace(cancelSpeech=lambda: events.append("cancelSpeech")),
		},
	)
	instance = SimpleNamespace(
		_get_playback_slider=lambda: slider,
	)

	assert rewind(instance, direction) is True
	assert events == [
		"sliderFocus",
		direction,
		"restoreFocus",
		"cancelSpeech",
		"restoreFocus",
	]
	assert messages == []


def test_voice_seek_without_a_visible_slider_reports_once_and_sends_nothing():
	messages = []
	events = []
	_, _, rewind = _load_methods(
		["_is_visible_playback_slider", "_get_playback_slider", "rewind_voice_message"],
		{
			"Role": SimpleNamespace(SLIDER="slider"),
			"message": messages.append,
			"_": lambda text: text,
			"api": SimpleNamespace(getFocusObject=lambda: None),
			"KeyboardInputGesture": SimpleNamespace(fromName=lambda name: events.append(name)),
			"speech": SimpleNamespace(cancelSpeech=lambda: events.append("cancel")),
		},
	)
	instance = SimpleNamespace(
		_get_playback_slider=lambda: None,
	)

	assert rewind(instance, "rightArrow") is False
	assert messages == ["Nothing is playing right now"]
	assert events == []


def test_voice_seek_restores_focus_and_reports_once_when_slider_turns_stale():
	messages = []
	events = []
	focus = SimpleNamespace(setFocus=lambda: events.append("restore"))
	slider = _slider(role="unknown")
	slider.setFocus = lambda: (_ for _ in ()).throw(RuntimeError("stale"))
	_, _, rewind = _load_methods(
		["_is_visible_playback_slider", "_get_playback_slider", "rewind_voice_message"],
		{
			"Role": SimpleNamespace(SLIDER="slider"),
			"message": messages.append,
			"_": lambda text: text,
			"api": SimpleNamespace(getFocusObject=lambda: focus),
			"KeyboardInputGesture": SimpleNamespace(fromName=lambda name: None),
			"speech": SimpleNamespace(cancelSpeech=lambda: events.append("cancel")),
			"log": SimpleNamespace(debug=lambda *args: events.append("logged")),
		},
	)
	instance = SimpleNamespace(_get_playback_slider=lambda: slider)

	assert rewind(instance, "rightArrow") is False
	assert events == ["logged", "restore"]
	assert messages == ["Nothing is playing right now"]


def test_playback_slider_detection_keeps_legacy_slider_role_compatibility():
	is_visible, _get_slider = _load_slider_helpers()
	legacy = _slider(role="slider", name="")

	assert is_visible(None, legacy)
