#!/usr/bin/env bash

set -e
set -u
set -o pipefail

exec gunicorn api:app \
  --access-logfile - \
  --error-logfile - \
  --capture-output \
  --log-level debug \
  --bind 0.0.0.0:$API_PORT