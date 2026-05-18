import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.survey_schemas import (
    AnswerSubmit,
    ScaleScoreItem,
    SessionResultResponse,
    SessionStateResponse,
    SurveyCreateRequest,
    SurveyUpdateRequest,
)


def test_survey_create_minimal_valid() -> None:
    payload = SurveyCreateRequest(methodology_id=1, name="S")
    assert payload.allow_individual_share is False
    assert payload.welcome_message is None


def test_survey_create_name_required_min_length() -> None:
    with pytest.raises(ValidationError):
        SurveyCreateRequest(methodology_id=1, name="")


def test_survey_update_partial_fields() -> None:
    valid = SurveyUpdateRequest(name="New name")
    assert valid.name == "New name"
    assert valid.welcome_message is None
    empty = SurveyUpdateRequest()
    assert empty.model_dump(exclude_unset=True) == {}


def test_answer_submit_text_length_bounds() -> None:
    sid = uuid.uuid4()
    with pytest.raises(ValidationError):
        AnswerSubmit(session_id=sid, question_id=1, text="")
    with pytest.raises(ValidationError):
        AnswerSubmit(session_id=sid, question_id=1, text="x" * 4001)
    valid = AnswerSubmit(session_id=sid, question_id=1, text="ok")
    assert valid.session_id == sid


def test_scale_score_item_value_bounds() -> None:
    with pytest.raises(ValidationError):
        ScaleScoreItem(scale_id=1, value=Decimal("-1"), confidence=Decimal("0.5"))
    with pytest.raises(ValidationError):
        ScaleScoreItem(scale_id=1, value=Decimal("101"), confidence=Decimal("0.5"))
    with pytest.raises(ValidationError):
        ScaleScoreItem(scale_id=1, value=Decimal("50"), confidence=Decimal("1.5"))
    ok = ScaleScoreItem(scale_id=1, value=Decimal("50"), confidence=Decimal("0.7"))
    assert ok.scale_id == 1


def test_session_state_response_from_attributes() -> None:
    class FakeSession:
        id = uuid.uuid4()
        survey_id = 1
        status = "in_progress"
        next_question_index = 3
        started_at = datetime.now(UTC)
        completed_at = None

    state = SessionStateResponse.model_validate(FakeSession())
    assert state.next_question_index == 3
    assert state.status == "in_progress"


def test_session_result_response_serializes_scores() -> None:
    sid = uuid.uuid4()
    result = SessionResultResponse(
        session_id=sid,
        status="completed",
        completed_at=datetime.now(UTC),
        scores=[
            ScaleScoreItem(scale_id=1, value=Decimal("80"), confidence=Decimal("0.9")),
        ],
    )
    payload = result.model_dump()
    assert payload["session_id"] == sid
    assert len(payload["scores"]) == 1
    assert payload["pinaba_url"] is None
