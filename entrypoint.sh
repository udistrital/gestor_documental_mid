#!/usr/bin/env bash

set -e
set -u
set -o pipefail

exec gunicorn api:app \
  --error-logfile - \
  --capture-output \
  --log-level info \
  --bind 0.0.0.0:$API_PORT