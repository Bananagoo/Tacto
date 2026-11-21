.PHONY: setup dev bench server bench-server web check check-server check-web contract sample mock manual fmt test kit

setup:
	cd server && uv sync
	cd web && pnpm install
	@test -f .env || cp .env.example .env
	@echo "Ready. Run: make dev"

# The product: server on :8000 and web on :5173, both reloading. Ctrl-C stops both.
dev:
	$(MAKE) -j2 server web

# Tooling: the real product on a virtual mat, plus the camera bench.
# Open http://localhost:5173/devtools/
bench:
	$(MAKE) -j2 bench-server web

server:
	cd server && uv run uvicorn tacto.main:app --reload --port 8000 --timeout-graceful-shutdown 2

bench-server:
	cd server && uv run uvicorn tacto_bench.main:app --reload --port 8000 --timeout-graceful-shutdown 2

web:
	cd web && pnpm dev

test:
	cd server && uv run pytest -q

check: check-server check-web

check-server:
	cd server && uv run ruff format --check . && uv run ruff check . && uv run pytest -q

check-web:
	cd web && pnpm exec prettier --check src devtools vite.config.ts && pnpm lint && pnpm build

# Refresh contract/ (JSON schemas and example messages) after a contract change
contract:
	cd server && uv run python -m tacto.contract_export

# Regenerate contract/sample-states.jsonl from the scripted run
sample:
	cd server && uv run python -m tacto_mock.sample

# For the UI team: replay the recorded sample on ws://localhost:8000/ws. No hardware needed.
mock:
	cd server && uv run uvicorn tacto_mock.main:app --port 8000

# The lab on a mat you set by hand, with the real solver. Open http://localhost:8000/manual
manual:
	cd server && uv run uvicorn tacto_bench.manual_main:app --port 8000 --timeout-graceful-shutdown 2

fmt:
	cd server && uv run ruff check --select I --fix . && uv run ruff format .
	cd web && pnpm exec prettier --write src devtools vite.config.ts

kit:
	@test -f kit/make_kit.py || (echo "kit/make_kit.py is not written yet (vision lane, phase 1)"; exit 1)
	cd server && uv run python ../kit/make_kit.py --out ../kit/out
