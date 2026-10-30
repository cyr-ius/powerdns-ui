import pytest

from app.dependencies import password_meets_policy


@pytest.mark.parametrize(
    ("password", "expected"),
    [
        ("Correct-Horse9", True),
        ("Short-Pass9", False),  # 11 characters
        ("correct-horse9", False),  # no uppercase letter
        ("CORRECT-HORSE9", False),  # no lowercase letter
        ("Correct-Horse", False),  # no digit
        ("CorrectHorse99", False),  # no symbol
    ],
)
def test_password_policy(password: str, expected: bool) -> None:
    assert password_meets_policy(password) is expected
