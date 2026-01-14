#!/usr/bin/env bash

set -e

python build.py

echo ""

bash hash.sh
