import ast
from pathlib import Path
import warnings


ROOT = Path(__file__).resolve().parents[1]


def test_update_api_url_uses_the_defined_repository_constant():
	source = (ROOT / "addon" / "GlobalPlugins" / "UnigramPlus" / "__init__.py").read_text(encoding="utf-8-sig")
	module = ast.parse(source)
	assignments = [
		node
		for node in module.body
		if isinstance(node, ast.Assign)
		and any(
			isinstance(target, ast.Name) and target.id in {"UPDATE_REPO", "UPDATE_API_URL"}
			for target in node.targets
		)
	]
	namespace = {}
	exec(compile(ast.Module(body=assignments, type_ignores=[]), "__init__.py", "exec"), namespace)

	assert namespace["UPDATE_API_URL"] == (
		"https://api.github.com/repos/keyang556/UnigramPlus/releases/latest"
	)


def test_python_sources_compile_without_syntax_warnings():
	paths = (
		ROOT / "addon" / "GlobalPlugins" / "UnigramPlus" / "__init__.py",
		ROOT / "addon" / "appModules" / "unigram.py",
		ROOT / "addon" / "appModules" / "unigramplus_text_window.py",
	)
	with warnings.catch_warnings():
		warnings.simplefilter("error", SyntaxWarning)
		for path in paths:
			compile(path.read_text(encoding="utf-8-sig"), str(path), "exec")


def test_text_window_helper_uses_a_private_module_name():
	app_modules = ROOT / "addon" / "appModules"
	assert (app_modules / "unigramplus_text_window.py").is_file()
	assert not (app_modules / "text_window.py").exists()

	unigram = ast.parse((app_modules / "unigram.py").read_text(encoding="utf-8-sig"))
	imports = [
		node
		for node in unigram.body
		if isinstance(node, ast.ImportFrom) and node.level == 1
	]
	assert any(
		node.module == "unigramplus_text_window"
		and [(name.name, name.asname) for name in node.names] == [("TextWindow", None)]
		for node in imports
	)
	assert not any(node.module == "text_window" for node in imports)


def test_release_bundle_excludes_python_bytecode_caches():
	build_vars = (ROOT / "buildVars.py").read_text(encoding="utf-8")

	assert '"**/__pycache__/*"' in build_vars
	assert '"**/*.pyc"' in build_vars
