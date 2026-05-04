from app.tasks.celery_app import celery_app, ping


def test_celery_broker_from_settings() -> None:
    assert celery_app.conf.broker_url
    assert "redis" in celery_app.conf.broker_url


def test_celery_default_queue_is_psychograph() -> None:
    assert celery_app.conf.task_default_queue == "psychograph"


def test_celery_serializer_is_json() -> None:
    assert celery_app.conf.task_serializer == "json"
    assert celery_app.conf.result_serializer == "json"
    assert "json" in celery_app.conf.accept_content


def test_ping_task_registered() -> None:
    assert "ping" in celery_app.tasks


def test_ping_eager_returns_pong() -> None:
    celery_app.conf.task_always_eager = True
    try:
        result = ping.delay()
        assert result.get(timeout=2) == "pong"
    finally:
        celery_app.conf.task_always_eager = False
