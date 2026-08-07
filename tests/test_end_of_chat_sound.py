import ast
import os
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = ROOT / "addon" / "appModules" / "unigram.py"


def _source_module():
	return ast.parse(SOURCE_PATH.read_text(encoding="utf-8"))


def _load_end_of_chat_sound_functions(namespace):
	functions = {
		node.name: node
		for node in _source_module().body
		if isinstance(node, ast.FunctionDef)
		and node.name in {"_get_end_of_chat_sound_path", "play_end_of_chat_sound"}
	}
	exec(
		compile(
			ast.Module(
				body=[
					functions["_get_end_of_chat_sound_path"],
					functions["play_end_of_chat_sound"],
				],
				type_ignores=[],
			),
			str(SOURCE_PATH),
			"exec",
		),
		namespace,
	)
	return namespace["play_end_of_chat_sound"]


def _load_message_list_item(namespace):
	message_class = next(
		node
		for node in _source_module().body
		if isinstance(node, ast.ClassDef) and node.name == "Message_list_item"
	)
	exec(
		compile(ast.Module(body=[message_class], type_ignores=[]), str(SOURCE_PATH), "exec"),
		namespace,
	)
	return namespace["Message_list_item"]


def _load_app_method(name, namespace):
	app_module = next(
		node
		for node in _source_module().body
		if isinstance(node, ast.ClassDef) and node.name == "AppModule"
	)
	method = next(
		node
		for node in app_module.body
		if isinstance(node, ast.FunctionDef) and node.name == name
	)
	method.decorator_list = []
	exec(compile(ast.Module(body=[method], type_ignores=[]), str(SOURCE_PATH), "exec"), namespace)
	return namespace[name]


def test_end_of_chat_sound_respects_setting_and_prefers_user_override(tmp_path):
	played = []
	typing_sound_calls = []
	enabled = {"value": True}
	base_dir = os.path.join("bundled", "media")
	custom_sound = tmp_path / "UnigramEndOfChat.wav"
	custom_sound.write_bytes(b"custom wave")
	namespace = {
		"os": os,
		"globalVars": SimpleNamespace(appArgs=SimpleNamespace(configPath=str(tmp_path))),
		"_END_OF_CHAT_SOUND_FILENAME": "EndOfChatDefault.wav",
		"_END_OF_CHAT_CUSTOM_SOUND_FILENAME": "UnigramEndOfChat.wav",
		"baseDir": base_dir,
		"conf": SimpleNamespace(get=lambda key: enabled["value"]),
		"playWaveFile": played.append,
		# The typing tracker owns a looping winsound playback.  The endpoint sound
		# must not replace it.
		"winsound": SimpleNamespace(PlaySound=lambda *args: typing_sound_calls.append(args)),
		"log": SimpleNamespace(debug=lambda *args, **kwargs: None),
	}
	play = _load_end_of_chat_sound_functions(namespace)

	assert play()
	assert played == [str(custom_sound)]
	assert typing_sound_calls == []

	custom_sound.unlink()
	assert play()
	assert played[-1] == os.path.join(base_dir, "EndOfChatDefault.wav")

	enabled["value"] = False
	assert not play()
	assert len(played) == 2


def test_down_arrow_plays_sound_only_at_last_message_and_preserves_navigation():
	sounds = []
	native_gestures = []
	focus_moves = []
	setting = {"value": "normal"}
	at_end = {"value": False}

	class ListItem:
		pass

	def script(**_kwargs):
		return lambda function: function

	message_class = _load_message_list_item(
		{
			"ListItem": ListItem,
			"script": script,
			"_": lambda text: text,
			"message": lambda text: None,
			"conf": SimpleNamespace(get=lambda key: setting["value"]),
			"play_end_of_chat_sound": lambda: sounds.append(True),
		}
	)
	item = message_class()
	item.appModule = SimpleNamespace(
		_is_last_message_in_chat=lambda obj: at_end["value"],
		script_moveFocusToTextMessage=lambda gesture: focus_moves.append(gesture)
	)
	gesture = SimpleNamespace(send=lambda: native_gestures.append(True))

	# A missing realized sibling is not proof that a virtualized message list has
	# reached its logical end.
	item.parent = SimpleNamespace(next=None)
	item.script_next_message(gesture)
	assert native_gestures == [True]
	assert sounds == []

	# Conversely, a trailing realized sibling must not suppress the notification
	# when UIA reports the logical final message.
	at_end["value"] = True
	item.parent = SimpleNamespace(next=object())
	item.script_next_message(gesture)
	assert sounds == [True]
	assert native_gestures == [True, True]
	assert focus_moves == []

	setting["value"] = "to_messages"
	item.script_next_message(gesture)
	assert sounds == [True, True]
	assert native_gestures == [True, True]
	assert focus_moves == [gesture]


def test_logical_last_message_detection_requires_complete_position_metadata():
	method = _load_app_method("_is_last_message_in_chat", {})
	instance = SimpleNamespace()

	assert method(
		instance,
		SimpleNamespace(positionInfo={"indexInGroup": 12, "similarItemsInGroup": 12}),
	)
	assert not method(
		instance,
		SimpleNamespace(positionInfo={"indexInGroup": 11, "similarItemsInGroup": 12}),
	)
	assert not method(
		instance,
		SimpleNamespace(positionInfo={"indexInGroup": 0, "similarItemsInGroup": 0}),
	)
	assert not method(instance, SimpleNamespace(positionInfo={}))
	assert not method(
		instance,
		SimpleNamespace(positionInfo={"indexInGroup": True, "similarItemsInGroup": True}),
	)


def test_alt_2_at_last_message_plays_end_of_chat_sound():
	sounds = []
	announcements = []
	sent = []
	focus = SimpleNamespace(name="Last message", parent=SimpleNamespace(next=object()))
	method = _load_app_method(
		"script_toLastMessage",
		{
			"api": SimpleNamespace(getFocusObject=lambda: focus),
			"play_end_of_chat_sound": lambda: sounds.append(True),
			"message": announcements.append,
			"KeyboardInputGesture": SimpleNamespace(
				fromName=lambda name: SimpleNamespace(send=lambda: sent.append(name))
			),
			"_": lambda text: text,
		},
	)
	endpoint = {"value": True}
	instance = SimpleNamespace(
		is_message_object=lambda obj: obj is focus,
		_is_last_message_in_chat=lambda obj: endpoint["value"],
	)

	assert method(instance, None)
	assert sounds == [True]
	assert announcements == ["Last message"]
	assert sent == []

	endpoint["value"] = False
	assert method(instance, None)
	assert sounds == [True]
	assert sent == ["end"]


def test_end_of_chat_sound_setting_is_enabled_by_default_and_persisted():
	config_source = (ROOT / "addon" / "appModules" / "cnf.py").read_text(encoding="utf-8")
	settings_source = (
		ROOT / "addon" / "GlobalPlugins" / "UnigramPlus" / "__init__.py"
	).read_text(encoding="utf-8-sig")

	assert '"play_end_of_chat_sound = boolean(default=True)"' in config_source
	assert '_("Play a sound when reaching the end of a chat")' in settings_source
	assert 'conf.set("play_end_of_chat_sound", self.play_end_of_chat_sound.IsChecked())' in settings_source
