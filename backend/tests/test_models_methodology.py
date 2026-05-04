from app.db.models import Methodology, Question, QuestionScale, Scale


def test_methodology_table_and_columns() -> None:
    cols = {c.name for c in Methodology.__table__.columns}
    assert cols == {
        "id",
        "name",
        "description",
        "category",
        "status",
        "author_id",
        "created_at",
        "published_at",
    }
    assert Methodology.__tablename__ == "methodologies"


def test_methodology_status_check_constraint_present() -> None:
    constraints = {c.name for c in Methodology.__table__.constraints}
    assert "methodologies_status_check" in constraints


def test_methodology_status_default_is_draft() -> None:
    column = Methodology.__table__.columns["status"]
    assert column.server_default is not None
    assert "draft" in str(column.server_default.arg)


def test_scale_columns_and_fk() -> None:
    cols = {c.name for c in Scale.__table__.columns}
    assert cols == {
        "id",
        "methodology_id",
        "name",
        "description",
        "min_value",
        "max_value",
        "interpretation_low",
        "interpretation_mid",
        "interpretation_high",
        "order_index",
    }
    fk = next(iter(Scale.__table__.columns["methodology_id"].foreign_keys))
    assert fk.column.table.name == "methodologies"
    assert fk.ondelete == "CASCADE"


def test_question_columns_and_jsonb() -> None:
    cols = {c.name for c in Question.__table__.columns}
    assert cols == {"id", "methodology_id", "text", "order_index", "theme_tags"}
    column = Question.__table__.columns["theme_tags"]
    assert column.type.__class__.__name__ == "JSONB"


def test_question_scale_composite_pk_and_weight_constraint() -> None:
    pk_cols = {c.name for c in QuestionScale.__table__.primary_key}
    assert pk_cols == {"question_id", "scale_id"}
    constraints = {c.name for c in QuestionScale.__table__.constraints}
    assert "question_scales_weight_range" in constraints
    weight = QuestionScale.__table__.columns["weight"]
    assert weight.type.precision == 3
    assert weight.type.scale == 2
