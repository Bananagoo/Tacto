.PHONY: camera-tool setup dev bench server bench-server web check check-server check-web contract sample mock manual fmt test kit

setup:
	cd server && uv sync
	cd web && pnpm install
	@test -f .env || cp .env.example .env
	-$(MAKE) camera-tool
	@echo "Ready. Run: make manual"

# uvc-util (MIT) sets the camera's exposure, which OpenCV cannot do on macOS. Pinned to a
# commit; built into server/vendor/, which is not committed. See server/tacto/vision/exposure.py.
UVC_UTIL_COMMIT := 8110da7025c95eea3096a7181af9a46c0cc7ac37
UVC_UTIL_DIR := server/vendor/uvc-util

camera-tool:
	@if [ "$$(uname)" != "Darwin" ]; then echo "camera-tool: macOS only, skipped"; \
	elif [ -x $(UVC_UTIL_DIR)/uvc-util ]; then echo "camera-tool: already built"; \
	else rm -rf $(UVC_UTIL_DIR) && mkdir -p server/vendor \
	  && git clone -q https://github.com/jtfrey/uvc-util.git $(UVC_UTIL_DIR) \
	  && git -C $(UVC_UTIL_DIR) checkout -q $(UVC_UTIL_COMMIT) \
	  && cd $(UVC_UTIL_DIR)/src \
	  && cc -w -o ../uvc-util -framework IOKit -framework Foundation \
	       uvc-util.m UVCController.m UVCType.m UVCValue.m \
	  && echo "camera-tool: built $(UVC_UTIL_DIR)/uvc-util"; fi

# The lab on the camera, with the web UI. The camera reader is not built yet: use make manual.
dev:
	$(MAKE) -j2 server web

# Tooling with the web dev tools: the hand-set mat (localhost:8000/manual) and the
# camera bench (localhost:5173/devtools/).
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
manual: bench-server

fmt:
	cd server && uv run ruff check --select I --fix . && uv run ruff format .
	cd web && pnpm exec prettier --write src devtools vite.config.ts

kit:
	cd server && uv run python ../kit/make_kit.py --out ../kit/out
