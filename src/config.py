from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ENVIRONMENT: str = "local"
    DATABASE_URL: str
    SECRET_KEY: str

    model_config = {"env_file": ".env"}

    @property
    def sqlalchemy_url(self) -> str:
        """Convert the Neon URL into the format SQLAlchemy + asyncpg needs."""
        url = self.DATABASE_URL.split("?")[0]  # drop the ?sslmode=require part
        url = url.replace("postgres://", "postgresql+asyncpg://")
        url = url.replace("postgresql://", "postgresql+asyncpg://")
        return url


settings = Settings()