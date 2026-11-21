"""Product code must never depend on test tooling.

Tooling (server/tacto_bench, web/devtools) may import the product. The reverse is
a mistake: it would ship code the product never runs and blur what is being tested.
"""

import ast
import re
from pathlib import Path

SERVER = Path(__file__).resolve().parents[1]
WEB = SERVER.parent / "web"


def imported_modules(path: Path) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(), filename=str(path))):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.add(node.module)
    return names


def test_server_product_does_not_import_tooling():
    offenders = [
        str(path.relative_to(SERVER))
        for path in sorted((SERVER / "tacto").rglob("*.py"))
        if any(name.split(".")[0] == "tacto_bench" for name in imported_modules(path))
    ]
    assert offenders == []


def test_server_product_holds_no_tooling_modules():
    # These lived in the product package before the split; they must not creep back.
    for name in ("devtools.py", "mock.py", "vision/bench.py"):
        assert not (SERVER / "tacto" / name).exists(), f"tacto/{name} belongs in tacto_bench"


def test_web_product_does_not_import_tooling():
    pattern = re.compile(r"""from\s+['"][^'"]*devtools[^'"]*['"]|import\(\s*['"][^'"]*devtools""")
    offenders = [
        str(path.relative_to(WEB))
        for path in sorted((WEB / "src").rglob("*.ts*"))
        if pattern.search(path.read_text())
    ]
    assert offenders == []


def test_web_product_holds_no_test_pages():
    leftovers = [
        str(path.relative_to(WEB))
        for path in sorted((WEB / "src").rglob("*"))
        if path.is_file() and re.search(r"(?i)test(bench|page|main)|test\.html", path.name)
    ]
    assert leftovers == []
