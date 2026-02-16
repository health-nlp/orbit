import os
import threading


_lock = threading.Lock()

# LOCAL_CTGOV_INDEX_PATH now can be controlled via environment variable.
# Default for normal runs (in docker) is /app/index.
# For CI/Test we will set LOCAL_CTGOV_INDEX_PATH via the workflow/environment to the test index folder.
ORBIT_CTGOV_INDEX_PATH = os.getenv("ORBIT_CTGOV_INDEX_PATH", "/app/index-ctgov")