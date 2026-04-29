import pytest
from pydantic import ValidationError

from app.schemas.auth_schemas import ChangePasswordRequest, EmailChangeRequest, RegisterRequest


def test_register_request_rejects_short_password():
    with pytest.raises(ValidationError):
        RegisterRequest(
            email="user@example.com",
            password="short",
            first_name="Ivan",
            last_name="Ivanov",
        )


def test_register_request_requires_first_name():
    with pytest.raises(ValidationError):
        RegisterRequest(
            email="user@example.com",
            password="Valid123!",
            last_name="Ivanov",
        )


def test_register_request_accepts_valid_password_and_fields():
    payload = RegisterRequest(
        email="user@example.com",
        password="Valid123!",
        first_name="Ivan",
        last_name="Ivanov",
    )
    assert payload.email == "user@example.com"
    assert payload.first_name == "Ivan"
    assert payload.last_name == "Ivanov"


def test_change_password_request_validates_new_password():
    payload = ChangePasswordRequest(new_password="Valid123!")
    assert payload.new_password == "Valid123!"


def test_email_change_request_validates_email():
    payload = EmailChangeRequest(new_email="new@example.com")
    assert payload.new_email == "new@example.com"

