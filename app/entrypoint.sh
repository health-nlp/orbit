#!/bin/sh
set -e

echo "MODE=$MODE"

if [ "$MODE" = "pubmed" ]; then
    exec sh index-pubmed.sh
    exit 0
elif [ "$MODE" = "ctgov" ]; then
    echo $ORBIT_CTGOV_INDEX_PATH
    echo $ORBIT_CTGOV_INDEX_PATH
    if [ -d $ORBIT_CTGOV_INDEX_PATH ] && [ "$(ls -A $ORBIT_CTGOV_INDEX_PATH)" ]; then
        exit 0
    fi
    uv run -m pybool_ir.cli ctgov download -b $ORBIT_CTGOV_BASELINE_PATH
    uv run -m pybool_ir.cli ctgov index -b $ORBIT_CTGOV_BASELINE_PATH -i $ORBIT_CTGOV_INDEX_PATH -s1
    exit 0
elif [ "$MODE" = "api" ]; then
    uv run -m fastapi dev main.py --host 0.0.0.0 --port $ORBIT_PORT
else 
    echo "UNKNOWN MODE=$MODE"
    exit 1
fi

exit 0
