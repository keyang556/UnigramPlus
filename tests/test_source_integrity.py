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
	)
	with warnings.catch_warnings():
		warnings.simplefilter("error", SyntaxWarning)
		for path in paths:
			compile(path.read_text(encoding="utf-8-sig"), str(path), "exec")
