import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

TEST_DB_PATH = Path("cie_test.db")
if TEST_DB_PATH.exists():
    TEST_DB_PATH.unlink()

os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH}"

# Ensure the package's `app` module can be imported via `from app...` as tests expect.
PROJECT_ROOT = Path(__file__).resolve().parents[1] / "app"
if str(PROJECT_ROOT.parent) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT.parent))
if "app" not in sys.modules:
    # Provide a plain namespace package style import path (the directory already has __init__.py)
    try:  # pragma: no cover - defensive
        __import__("app")
    except Exception:  # noqa: BLE001
        pass

from preciagro.packages.engines.crop_intelligence.app.main import app  # noqa: E402
from preciagro.packages.engines.crop_intelligence.app.db.session import engine  # noqa: E402
from preciagro.packages.engines.crop_intelligence.app.db.base import Base  # noqa: E402


@pytest.fixture(autouse=True)
def reset_db():
    """Drop and recreate all tables to isolate tests."""
    Base.metadata.drop_all(bind=engine, checkfirst=True)
    Base.metadata.create_all(bind=engine, checkfirst=True)
    yield


@pytest.fixture
def client():
    return TestClient(app)
