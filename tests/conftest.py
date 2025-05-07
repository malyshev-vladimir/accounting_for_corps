import pytest
import models.member


@pytest.fixture
def sample_member():
    return models.member.Member(
        email="test@example.com",
        last_name="Testov",
        first_name="Test",
        start_balance=0.0
    )
