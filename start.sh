#!/usr/bin/env bash
set -euo pipefail

PORT="${PORT:-8000}"
uvicorn src.web.app:app --host 0.0.0.0 --port "$PORT"
