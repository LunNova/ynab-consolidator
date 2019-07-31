#!/bin/sh

set -euo pipefail

cd /code/

python app.py "$@"
