from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite:///./donor_uc_dev.db"
    secret_key: str = "donor-uc-dev-secret-change-me"
    access_token_minutes: int = 60 * 12
    cors_origins: str = "http://localhost:3000,http://localhost:3001,http://127.0.0.1:3000,http://127.0.0.1:3001"

    class Config:
        env_file = ".env"


settings = Settings()
