"""Запускає src.main:app для контрактної перевірки schemathesis (logs/lab5-scope.md, пп. 11, 12).

Засіває in-memory сховище токенів трьома тестовими токенами у форматі фікстур
тестів ({"userId": str, "role": значення User.roles}) і слухає 127.0.0.1:8765.

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
SEED = {"guest-token": "GUEST", "host-token": "HOST", "moderator-token": "MODERATOR"}

for token, role in SEED.items():
    TOKENS[token] = {"userId": str(uuid.uuid4()), "role": role}

if __name__ == "__main__":
    uvicorn.run(app, host=HOST, port=PORT)
