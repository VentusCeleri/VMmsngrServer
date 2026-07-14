import pytest

from app.core.rate_limit import rate_limiter


@pytest.fixture(autouse=True)
def clear_rate_limiter() -> None:
    rate_limiter.clear()
