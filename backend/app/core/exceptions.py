class AppError(Exception):
    status_code = 500
    default_message = "Внутренняя ошибка сервера"

    def __init__(self, message: str | None = None) -> None:
        self.message = message or self.default_message
        super().__init__(self.message)


class NotFoundError(AppError):
    status_code = 404
    default_message = "Объект не найден"


class AlreadyExistsError(AppError):
    status_code = 400
    default_message = "Объект уже существует"


class AuthenticationError(AppError):
    status_code = 401
    default_message = "Ошибка аутентификации"


class ForbiddenError(AppError):
    status_code = 403
    default_message = "Доступ запрещен"


class ConflictError(AppError):
    status_code = 409
    default_message = "Конфликт данных"


class GoneError(AppError):
    status_code = 410
    default_message = "Ресурс больше недоступен"


class UnprocessableError(AppError):
    status_code = 422
    default_message = "Данные не прошли бизнес-валидацию"


class LockedError(AppError):
    status_code = 423
    default_message = "Ресурс заблокирован"
