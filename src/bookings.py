"""Псевдонім `src.services.bookings` для tests/unit, які імпортують `src.bookings`.

Це той самий об'єкт модуля, а не копія імен: підміна `src.bookings.now` у тестах має
діяти на сервісний шар. Файл можна видалити, коли тести перейдуть на `src.services.bookings`.
"""
import sys

from src.services import bookings

sys.modules[__name__] = bookings
