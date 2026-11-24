from fastapi import FastAPI
from sqlalchemy import text

from src.config import settings
from src.database import engine
from src.products.router import router as products_router
from src.auth.router import router as auth_router
from src.cart.router import router as cart_router


app = FastAPI(title="Shop Scale")

app.include_router(products_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(cart_router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok", "environment": settings.ENVIRONMENT}


@app.get("/health/db")
async def health_db():
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"database": "ok"}
    except Exception as e:
        return {"database": "unreachable", "error": str(e)}