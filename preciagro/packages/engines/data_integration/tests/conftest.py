import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def pytest_configure(config=None):
    """Ensure repository root (the directory that contains the `preciagro` package)
    is on sys.path so tests can import `preciagro.*` modules.

    This is intentionally defensive: it walks upward from the tests folder until
    it finds a directory that contains a `preciagro` directory and inserts that
    parent directory into sys.path.
    """
    here = Path(__file__).resolve()
    cur = here
    # walk up to filesystem root looking for a folder that contains 'preciagro'
    while True:
        parent = cur.parent
        if (parent / "preciagro").exists():
            root = parent
            sys.path.insert(0, str(root))
            logger.debug("Added project root to sys.path: %s", root)
            return
        if parent == cur:
            # reached filesystem root
            break
        cur = parent

    # fallback: insert two levels up from this file (best-effort)
    fallback = here.parents[5] if len(here.parents) >= 6 else here.parents[-1]
    sys.path.insert(0, str(fallback))
    logger.debug("Fallback added to sys.path: %s", fallback)
