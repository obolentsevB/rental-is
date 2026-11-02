"""Збирає застосунок rental-is. Обсяг і обмеження — logs/lab5-scope.md."""
from fastapi import FastAPI

from src.errors import register_error_handlers
from src.routers import bookings, listings

ROUTERS = (listings.router, bookings.router)

app = FastAPI(title="rental-is")
register_error_handlers(app, ROUTERS)
for router in ROUTERS:
    app.include_router(router)
