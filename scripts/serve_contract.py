"""Запускає src.main:app для контрактної перевірки schemathesis (logs/lab5-scope.md, пп. 11, 12).

Засіває in-memory сховище токенів трьома тестовими токенами у форматі фікстур
тестів ({"userId": str, "role": значення User.roles}) і слухає 127.0.0.1:8765.

Ліміт h11 на рядок запиту й заголовки піднято з 16 КБ до 1 МБ. schemathesis 4.33.1 генерує
query-рядки `GET /listings` довжиною близько 65 КБ, і зі стандартним лімітом uvicorn відповідає
400 «Invalid HTTP request received.» ще до застосунку. Контракт обмежень транспорту не описує,
тому перевірка має дійти до коду. Звичайний запуск `uvicorn src.main:app` цей ліміт не змінює.

Запуск із кореня репозиторію: python scripts/serve_contract.py
"""
import sys
import uuid
from pathlib import Path

import uvicorn

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.auth import TOKENS  # noqa: E402
from src.main import app  # noqa: E402

HOST, PORT = "127.0.0.1", 8765
MAX_REQUEST_HEAD_BYTES = 1024 * 1024
SEED = {"guest-token": "GUEST", "host-token": "HOST", "moderator-token": "MODERATOR"}

for token, role in SEED.items():
    TOKENS[token] = {"userId": str(uuid.uuid4()), "role": role}

if __name__ == "__main__":
    uvicorn.run(app, host=HOST, port=PORT, h11_max_incomplete_event_size=MAX_REQUEST_HEAD_BYTES)
