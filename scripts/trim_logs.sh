#!/usr/bin/env bash
set -e
LOGDIR="$(dirname "$0")/../logs"
mkdir -p "$LOGDIR"
for f in "$LOGDIR"/*.log; do
  [ -f "$f" ] || continue
  # >5MB直接清空，否则保留末尾5000行
  if [ $(stat -c%s "$f") -gt $((5*1024*1024)) ]; then
    : > "$f"
  else
    tail -n 5000 "$f" > "$f.tmp" && mv "$f.tmp" "$f"
  fi
done
