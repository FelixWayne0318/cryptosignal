#!/usr/bin/env bash
set -e
export PATH="$HOME/.local/bin:$PATH"
VENV="$HOME/ats-analyzer/.venv"
if [ -f "$VENV/bin/activate" ]; then . "$VENV/bin/activate"; fi
