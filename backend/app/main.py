from fastapi import FastAPI

from app.api.accounts import router as accounts_router
from app.api.auth import router as auth_router
from app.api.categories import router as categories_router
from app.api.household import router as household_router
from app.api.stats import router as stats_router
from app.api.transactions import router as transactions_router
from app.api.health import router as health_router

# Every route carries the /api prefix on purpose. On Vercel the rewrite
# /api/(.*) -> /api/index hands the function the *original* path, so the app
# must answer on /api/health both in production and behind the local Vite proxy.
app = FastAPI(
    title="Wallet API",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url=None,
    openapi_url="/api/openapi.json",
)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(accounts_router)
app.include_router(categories_router)
app.include_router(transactions_router)
app.include_router(household_router)
app.include_router(stats_router)
