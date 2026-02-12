#!/bin/sh
set -e

echo "MODE=$MODE"

if [ "$MODE" = "pubmed" ]; then
    exec sh index-pubmed.sh
elif [ "$MODE" = "ctgov" ]; then
    echo baseline: $ORBIT_CTGOV_BASELINE_PATH
    echo index: $ORBIT_CTGOV_INDEX_PATH
    uv run -m pybool_ir.cli ctgov download -b $ORBIT_CTGOV_BASELINE_PATH
    uv run -m pybool_ir.cli ctgov index -b $ORBIT_CTGOV_BASELINE_PATH -i $ORBIT_CTGOV_INDEX_PATH -s1
elif [ "$MODE" = "api" ]; then
    uv run -m fastapi dev main.py --host 0.0.0.0 --port 8333
else 
    echo "UNKNOWN MODE=$MODE"
    exit 1
fi
