"""Test suite for temporal logic engine."""

import pytest
import pytest_asyncio

if not hasattr(pytest_asyncio, "async_test"):

    def async_test(func):
        """Provide backward-compatible decorator for async tests."""
        return pytest.mark.asyncio(func)

    pytest_asyncio.async_test = async_test  # type: ignore[attr-defined]
