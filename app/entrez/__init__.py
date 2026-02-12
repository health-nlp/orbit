import os
import threading


_lock = threading.Lock()

# LOCAL_PUBMED_INDEX_PATH now can be controlled via environment variable.
# Default for normal runs (in docker) is /app/index.
# For CI/Test we will set LOCAL_PUBMED_INDEX_PATH via the workflow/environment to the test index folder.
LOCAL_PUBMED_INDEX_PATH = os.getenv("LOCAL_PUBMED_INDEX_PATH", "/app/index")