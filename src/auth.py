"""In-memory сховище токенів і залежності автентифікації (logs/lab5-scope.md, п. 11).

Users/Auth не реалізуються: тести засівають сховище фікстурами.
Значення ролі — з `User.roles` (api/openapi.yaml): GUEST, HOST, MODERATOR.
Залежності виконуються до валідації тіла, тому 401 і 403 мають пріоритет над 422.
"""
from typing import Annotated

from fastapi import Depends, Header

from src.errors import ProblemError

TOKENS: dict[str, dict] = {}  # token → {"userId": str, "role": str}


def optional_user(authorization: Annotated[str | None, Header()] = None) -> dict | None:
    """Користувач за bearer-токеном або None, якщо токена немає чи він невідомий."""
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer":
        return None
    return TOKENS.get(token.strip())


def require_user(user: Annotated[dict | None, Depends(optional_user)]) -> dict:
    if user is None:
        raise ProblemError("UNAUTHENTICATED", "Дія потребує входу в систему.")
    return user


def require_non_moderator(user: Annotated[dict, Depends(require_user)]) -> dict:
    if user["role"] == "MODERATOR":
        raise ProblemError("FORBIDDEN", "Дія не дозволена цій ролі.")
    return user


def require_moderator(user: Annotated[dict, Depends(require_user)]) -> dict:
    if user["role"] != "MODERATOR":
        raise ProblemError("FORBIDDEN", "Дія доступна лише модератору.")
    return user


OptionalUser = Annotated[dict | None, Depends(optional_user)]
User = Annotated[dict, Depends(require_user)]
NonModerator = Annotated[dict, Depends(require_non_moderator)]
Moderator = Annotated[dict, Depends(require_moderator)]
