from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.methodology_schemas import (
    MethodologyCreateRequest,
    MethodologyResponse,
    MethodologyUpdateRequest,
    QuestionCreateRequest,
    QuestionResponse,
    QuestionScaleItem,
    QuestionScaleSetRequest,
    ScaleCreateRequest,
    ScaleResponse,
)


def test_methodology_create_ok() -> None:
    req = MethodologyCreateRequest(name="CBT", category="psychometric")
    assert req.name == "CBT"
    assert req.description is None


def test_methodology_create_blank_name_fails() -> None:
    with pytest.raises(ValidationError):
        MethodologyCreateRequest(name="", category="psychometric")


def test_methodology_create_missing_category_fails() -> None:
    with pytest.raises(ValidationError):
        MethodologyCreateRequest(name="CBT")  # type: ignore[call-arg]


def test_methodology_update_partial_ok() -> None:
    req = MethodologyUpdateRequest(name="New name")
    assert req.name == "New name"
    assert req.category is None


def test_methodology_response_from_orm_dict() -> None:
    payload = {
        "id": 1,
        "name": "M",
        "description": None,
        "category": "cbt",
        "status": "draft",
        "author_id": None,
        "created_at": datetime(2026, 5, 4, tzinfo=UTC),
        "published_at": None,
    }
    resp = MethodologyResponse.model_validate(payload)
    assert resp.status == "draft"


def test_scale_create_defaults() -> None:
    req = ScaleCreateRequest(name="Distortion")
    assert req.min_value == 0
    assert req.max_value == 100
    assert req.order_index == 0


def test_scale_create_blank_name_fails() -> None:
    with pytest.raises(ValidationError):
        ScaleCreateRequest(name="")


def test_scale_response_validates() -> None:
    payload = {
        "id": 1,
        "methodology_id": 1,
        "name": "S",
        "description": None,
        "min_value": 0,
        "max_value": 100,
        "interpretation_low": None,
        "interpretation_mid": None,
        "interpretation_high": None,
        "order_index": 0,
    }
    resp = ScaleResponse.model_validate(payload)
    assert resp.name == "S"


def test_question_create_with_tags() -> None:
    req = QuestionCreateRequest(text="Расскажите.", theme_tags=["cbt", "family"])
    assert req.theme_tags == ["cbt", "family"]


def test_question_create_blank_text_fails() -> None:
    with pytest.raises(ValidationError):
        QuestionCreateRequest(text="")


def test_question_response_no_tags() -> None:
    resp = QuestionResponse.model_validate(
        {
            "id": 1,
            "methodology_id": 1,
            "text": "Q?",
            "order_index": 0,
            "theme_tags": None,
        }
    )
    assert resp.theme_tags is None


def test_question_scale_item_weight_in_range() -> None:
    item = QuestionScaleItem(scale_id=1, weight=Decimal("0.75"))
    assert item.weight == Decimal("0.75")


@pytest.mark.parametrize("bad_weight", ["1.5", "-0.1", "2", "-0.0001"])
def test_question_scale_item_weight_out_of_range_fails(bad_weight: str) -> None:
    with pytest.raises(ValidationError):
        QuestionScaleItem(scale_id=1, weight=Decimal(bad_weight))


def test_question_scale_set_request_min_one_item() -> None:
    with pytest.raises(ValidationError):
        QuestionScaleSetRequest(weights=[])


def test_question_scale_set_request_ok() -> None:
    req = QuestionScaleSetRequest(
        weights=[
            QuestionScaleItem(scale_id=1, weight=Decimal("0.8")),
            QuestionScaleItem(scale_id=2, weight=Decimal("0.2")),
        ]
    )
    assert len(req.weights) == 2
