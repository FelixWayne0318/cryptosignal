#!/usr/bin/env bash
set -e
flock -n /tmp/ats_analyzer.lock -c "$*"
