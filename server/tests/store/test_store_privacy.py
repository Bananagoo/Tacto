"""What stays inside `tacto/store/`: the tables, and every query, built without string pasting."""

import ast
import re
from pathlib import Path

PRODUCT = Path(__file__).resolve().parents[2] / "tacto"
STORE = PRODUCT / "store"

SQL_WORD = re.compile(r"\b(select|insert|update|delete|drop|pragma|where|values)\b", re.IGNORECASE)


def parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def imports_store_tables(tree: ast.Module) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(alias.name.endswith("store.tables") for alias in node.names):
                return True
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            names = {alias.name for alias in node.names}
            if module.endswith("store.tables"):
                return True
            if module.split(".")[-1] == "store" and "tables" in names:
                return True
    return False


def formatted_strings(tree: ast.Module) -> list[str]:
    """The literal text of every f-string, `%` format and `.format()` call in the module."""
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.JoinedStr):
            pieces = [part.value for part in node.values if isinstance(part, ast.Constant)]
            found.append("".join(str(piece) for piece in pieces))
        elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mod | ast.Add):
            for side in (node.left, node.right):
                if isinstance(side, ast.Constant) and isinstance(side.value, str):
                    found.append(side.value)
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "format"
            and isinstance(node.func.value, ast.Constant)
        ):
            found.append(str(node.func.value.value))
    return found


def test_only_the_store_package_sees_the_tables():
    offenders = [
        str(path.relative_to(PRODUCT))
        for path in sorted(PRODUCT.rglob("*.py"))
        if STORE not in path.parents and imports_store_tables(parse(path))
    ]
    assert offenders == []


def test_the_store_package_does_not_export_the_tables():
    # `from tacto.store import LessonRow` must not work: the package re-exports nothing.
    init = parse(STORE / "__init__.py")
    assert not any(isinstance(node, ast.Import | ast.ImportFrom) for node in ast.walk(init))


def test_no_sql_is_built_by_formatting_strings():
    offenders = [
        f"{path.name}: {text!r}"
        for path in sorted(STORE.glob("*.py"))
        for text in formatted_strings(parse(path))
        if SQL_WORD.search(text)
    ]
    assert offenders == []


def test_no_raw_sql_text_is_used():
    # `sqlalchemy.text` runs a string as SQL; the query builder binds every value instead.
    offenders = [
        path.name
        for path in sorted(STORE.glob("*.py"))
        for node in ast.walk(parse(path))
        if isinstance(node, ast.ImportFrom)
        and (node.module or "").split(".")[0] in ("sqlalchemy", "sqlmodel")
        and any(alias.name == "text" for alias in node.names)
    ]
    assert offenders == []


def test_the_formatted_string_check_catches_pasted_sql():
    pasted = ast.parse(
        "a = f\"SELECT * FROM learner WHERE nickname = '{name}'\"\n"
        "b = 'delete from learner where id = %s' % learner_id\n"
        "c = 'update learner set nickname = {}'.format(name)\n"
        "d = 'drop table ' + table\n"
    )

    assert len([text for text in formatted_strings(pasted) if SQL_WORD.search(text)]) == 4
