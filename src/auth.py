"""In-memory сховище токенів (logs/lab5-scope.md, п. 11).

Users/Auth не реалізуються: тести засівають сховище фікстурами.
Значення ролі — з `User.roles` (api/openapi.yaml): GUEST, HOST, MODERATOR.
"""

TOKENS: dict[str, dict] = {}  # token → {"userId": str, "role": str}
