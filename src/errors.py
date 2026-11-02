"""Модель помилок Problem (RFC 9457): єдиний виняток сервісів і обробники застосунку."""
import uuid
from collections.abc import Sequence

from fastapi import APIRouter, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.routing import Match

# Код → (HTTP-статус, title); статуси й заголовки — з прикладів api/openapi.yaml.
PROBLEMS = {
    "UNAUTHENTICATED": (401, "Потрібен вхід"),
    "FORBIDDEN": (403, "Дію не дозволено"),
    "OWN_LISTING": (403, "Власне житло"),
    "NOT_FOUND": (404, "Не знайдено"),
    "STATE_CONFLICT": (409, "Дія неможлива в поточному стані"),
    "LISTING_UNPUBLISHED": (409, "Житло зняте з публікації"),
    "DATES_UNAVAILABLE": (409, "Дати недоступні"),
    "VALIDATION_FAILED": (422, "Запит порушує схему"),
    "PHOTO_INVALID": (422, "Фотографії не відповідають вимогам"),
    "MIN_NIGHTS": (422, "Менше 1 ночі"),
    "GUESTS_OUT_OF_RANGE": (422, "Кількість осіб поза межами"),
    "CHECKIN_TOO_SOON": (422, "Замало часу до заїзду"),
    "INTERNAL_ERROR": (500, "Збій системи"),
}

NOT_FOUND_DETAIL = "Ресурс не існує або недоступний."


class ProblemError(Exception):
    """Відмова з кодом зі схеми Problem; `extra` — додаткові поля відповіді."""

    def __init__(self, code: str, detail: str | None = None, **extra):
        super().__init__(detail)
        self.code, self.detail, self.extra = code, detail, extra


def not_found() -> ProblemError:
    return ProblemError("NOT_FOUND", NOT_FOUND_DETAIL)


def problem_response(code: str, detail: str | None = None, **extra) -> JSONResponse:
    status, title = PROBLEMS[code]
    body = {
        "type": f"urn:rental-is:problem:{code.lower().replace('_', '-')}",
        "title": title,
        "status": status,
        "code": code,
        "correlationId": str(uuid.uuid4()),
    }
    if detail is not None:
        body["detail"] = detail
    body.update(extra)
    return JSONResponse(body, status_code=status, media_type="application/problem+json")


async def handle_problem(request: Request, exc: ProblemError):
    return problem_response(exc.code, exc.detail, **exc.extra)


async def handle_validation(request: Request, exc: RequestValidationError):
    error = exc.errors()[0]
    field = ".".join(str(part) for part in error["loc"][1:]) or str(error["loc"][0])
    return problem_response("VALIDATION_FAILED", f"{field}: {error['msg']}")


def allowed_methods(request: Request) -> str:
    """Методи всіх маршрутів, шлях яких збігається із запитом (для заголовка Allow, RFC 9110).

    `app.routes` містить підключені роутери лише як один лінивий елемент без методів,
    тому їхні маршрути беруться з самих роутерів (`app.state.routers`).
    """
    app = request.app
    routes = [*app.routes, *(route for router in app.state.routers for route in router.routes)]
    methods = set()
    for route in routes:
        match, _ = route.matches(request.scope)
        if match != Match.NONE:
            methods |= getattr(route, "methods", None) or set()
    return ", ".join(sorted(methods))


async def handle_http(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        return problem_response("NOT_FOUND", NOT_FOUND_DETAIL)
    if exc.status_code == 400:
        # Тіло, яке не вдається розібрати; статусу 400 у контракті немає — це порушення схеми.
        return problem_response("VALIDATION_FAILED", "Тіло запиту не вдається розібрати як JSON.")
    if exc.status_code == 405:
        return JSONResponse({"detail": exc.detail}, status_code=405, headers={"Allow": allowed_methods(request)})
    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code, headers=exc.headers)


async def handle_internal(request: Request, exc: Exception):
    return problem_response("INTERNAL_ERROR")


def register_error_handlers(app: FastAPI, routers: Sequence[APIRouter]) -> None:
    app.state.routers = routers
    app.add_exception_handler(ProblemError, handle_problem)
    app.add_exception_handler(RequestValidationError, handle_validation)
    app.add_exception_handler(StarletteHTTPException, handle_http)
    app.add_exception_handler(Exception, handle_internal)
