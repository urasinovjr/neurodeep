from app.db.models import (
    Invitation,
    PinabaArtifact,
    ScaleScore,
    Survey,
    SurveySession,
    UserProfile,
)


def test_survey_table_and_columns() -> None:
    cols = {c.name for c in Survey.__table__.columns}
    assert cols == {
        "id",
        "researcher_id",
        "methodology_id",
        "name",
        "welcome_message",
        "start_date",
        "end_date",
        "allow_individual_share",
        "status",
        "invite_token",
        "created_at",
    }
    assert Survey.__tablename__ == "surveys"


def test_survey_status_check_constraint() -> None:
    constraints = {c.name for c in Survey.__table__.constraints}
    assert "surveys_status_check" in constraints


def test_survey_invite_token_unique() -> None:
    assert Survey.__table__.columns["invite_token"].unique is True


def test_survey_fks() -> None:
    researcher_fk = next(iter(Survey.__table__.columns["researcher_id"].foreign_keys))
    assert researcher_fk.column.table.name == "users"
    methodology_fk = next(iter(Survey.__table__.columns["methodology_id"].foreign_keys))
    assert methodology_fk.column.table.name == "methodologies"


def test_invitation_columns_and_uuid_token() -> None:
    cols = {c.name for c in Invitation.__table__.columns}
    assert cols == {
        "id",
        "survey_id",
        "token",
        "email",
        "department",
        "used_at",
        "reminded_count",
        "created_at",
    }
    assert Invitation.__tablename__ == "invitations"
    assert Invitation.__table__.columns["token"].unique is True
    assert Invitation.__table__.columns["token"].type.__class__.__name__ == "Uuid"
    fk = next(iter(Invitation.__table__.columns["survey_id"].foreign_keys))
    assert fk.ondelete == "CASCADE"


def test_survey_session_columns_and_uuid_pk() -> None:
    cols = {c.name for c in SurveySession.__table__.columns}
    assert cols == {
        "id",
        "survey_id",
        "invitation_id",
        "user_id",
        "respondent_anon_id",
        "consent_given_at",
        "started_at",
        "completed_at",
        "next_question_index",
        "status",
        "profile_json",
        "pinaba_image_key",
        "created_at",
    }
    pk_cols = {c.name for c in SurveySession.__table__.primary_key}
    assert pk_cols == {"id"}
    assert SurveySession.__table__.columns["id"].type.__class__.__name__ == "Uuid"
    assert SurveySession.__table__.columns["respondent_anon_id"].type.__class__.__name__ == "Uuid"


def test_survey_session_status_check_constraint() -> None:
    constraints = {c.name for c in SurveySession.__table__.constraints}
    assert "survey_sessions_status_check" in constraints


def test_survey_session_profile_json_is_jsonb() -> None:
    column = SurveySession.__table__.columns["profile_json"]
    assert column.type.__class__.__name__ == "JSONB"


def test_survey_session_no_text_of_answer_columns() -> None:
    forbidden = {
        "answer_text",
        "response_text",
        "user_text",
        "raw_answer",
        "raw_response",
        "message_body",
        "chat_message",
    }
    cols = {c.name for c in SurveySession.__table__.columns}
    assert cols.isdisjoint(forbidden)


def test_scale_score_columns_and_constraints() -> None:
    cols = {c.name for c in ScaleScore.__table__.columns}
    assert cols == {"id", "session_id", "scale_id", "value", "confidence", "created_at"}
    constraints = {c.name for c in ScaleScore.__table__.constraints}
    assert "scale_scores_value_range" in constraints
    assert "scale_scores_confidence_range" in constraints

    value_col = ScaleScore.__table__.columns["value"]
    assert value_col.type.precision == 5
    assert value_col.type.scale == 2

    conf_col = ScaleScore.__table__.columns["confidence"]
    assert conf_col.type.precision == 3
    assert conf_col.type.scale == 2

    fk = next(iter(ScaleScore.__table__.columns["session_id"].foreign_keys))
    assert fk.column.table.name == "survey_sessions"
    assert fk.ondelete == "CASCADE"


def test_pinaba_artifact_columns_and_unique_public_uuid() -> None:
    cols = {c.name for c in PinabaArtifact.__table__.columns}
    assert cols == {
        "id",
        "session_id",
        "image_key",
        "public_uuid",
        "expires_at",
        "created_at",
    }
    assert PinabaArtifact.__table__.columns["public_uuid"].unique is True
    assert PinabaArtifact.__table__.columns["public_uuid"].type.__class__.__name__ == "Uuid"


def test_user_profile_columns_and_unique_user_id() -> None:
    cols = {c.name for c in UserProfile.__table__.columns}
    assert cols == {"id", "user_id", "encrypted_data", "key_version", "updated_at"}
    assert UserProfile.__table__.columns["user_id"].unique is True
    assert UserProfile.__table__.columns["encrypted_data"].type.__class__.__name__ == "LargeBinary"
    fk = next(iter(UserProfile.__table__.columns["user_id"].foreign_keys))
    assert fk.column.table.name == "users"
    assert fk.ondelete == "CASCADE"


def test_survey_relationships_loaded() -> None:
    rel_names = {r.key for r in Survey.__mapper__.relationships}
    assert {"invitations", "sessions"}.issubset(rel_names)


def test_survey_session_relationships_loaded() -> None:
    rel_names = {r.key for r in SurveySession.__mapper__.relationships}
    assert {"survey", "invitation", "scale_scores", "pinaba_artifacts"}.issubset(rel_names)
