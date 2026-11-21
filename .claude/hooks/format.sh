#!/bin/bash
# PostToolUse hook: format the file Claude just edited. Never blocks (always exits 0).
# Uses python3 to read the hook's JSON from stdin so jq is not required.

file=$(python3 -c 'import json,sys; print(json.load(sys.stdin).get("tool_input",{}).get("file_path",""))' 2>/dev/null)
root="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null)}"

[[ -n "$file" && -f "$file" && -n "$root" ]] || exit 0

case "$file" in
  "$root"/server/*.py | "$root"/kit/*.py)
    ruff="$root/server/.venv/bin/ruff"
    if [[ -x "$ruff" ]]; then
      # Import sorting only. Removing unused imports here would delete an import
      # Claude added one edit before the code that uses it.
      "$ruff" check --select I --fix --quiet --config "$root/server/pyproject.toml" "$file" >/dev/null 2>&1
      "$ruff" format --quiet --config "$root/server/pyproject.toml" "$file" >/dev/null 2>&1
    fi
    ;;
  "$root"/web/src/* | "$root"/web/*.ts | "$root"/web/*.json)
    prettier="$root/web/node_modules/.bin/prettier"
    case "$file" in
      *.ts | *.tsx | *.css | *.json)
        [[ -x "$prettier" ]] && "$prettier" --write --log-level silent "$file" >/dev/null 2>&1
        ;;
    esac
    ;;
esac

exit 0
