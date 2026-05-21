#!/usr/bin/env bash
set -euo pipefail
if [ "$#" -lt 2 ]; then
  echo "Usage: $0 output.root input1.root [input2.root ...]" >&2
  exit 1
fi
OUTPUT="$1"
shift
hadd -f "$OUTPUT" "$@"
