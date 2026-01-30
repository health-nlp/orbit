#!/bin/sh
set -e

echo "MODE=$MODE"

if [ "$MODE" = "full" ]; then
    echo "Running DATA BUILDER (in full mode)"
    exec sh index-pubmed.sh

elif [ "$MODE" = "test" ]; then
    echo "Running DATA BUILDER (in test mode)"
    exec sh index-pubmed.sh --test

elif [ "$MODE" = "api" ]; then
    echo "Starting API"
    ls -alh
    pwd
    exec uv run -m fastapi dev main.py --host 0.0.0.0 --port 8333

else 
    echo "UNKNOWN MODE=$MODE"
    exit 1

fi