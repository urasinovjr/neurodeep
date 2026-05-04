from fastapi import HTTPException


class NotFoundError(HTTPException):
    def __init__(self, detail: str = "Не найдено") -> None:
        super().__init__(status_code=404, detail=detail)


class AlreadyExistsError(HTTPException):
    def __init__(self, detail: str = "Уже существует") -> None:
        super().__init__(status_code=400, detail=detail)


class AuthenticationError(HTTPException):
    def __init__(self, detail: str = "Не авторизован") -> None:
        super().__init__(status_code=401, detail=detail)


class ForbiddenError(HTTPException):
    def __init__(self, detail: str = "Доступ запрещён") -> None:
        super().__init__(status_code=403, detail=detail)


class ConflictError(HTTPException):
    def __init__(self, detail: str = "Конфликт состояния") -> None:
        super().__init__(status_code=409, detail=detail)


class GoneError(HTTPException):
    def __init__(self, detail: str = "Ресурс больше недоступен") -> None:
        super().__init__(status_code=410, detail=detail)


class UnprocessableError(HTTPException):
    def __init__(self, detail: str = "Невозможно обработать") -> None:
        super().__init__(status_code=422, detail=detail)


class LockedError(HTTPException):
    def __init__(self, detail: str = "Ресурс заблокирован") -> None:
        super().__init__(status_code=423, detail=detail)
