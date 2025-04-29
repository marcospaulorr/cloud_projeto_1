from pydantic import PostgresDsn, Field
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: PostgresDsn = Field(..., env="DATABASE_URL")
    secret_key: str      = Field(..., env="SECRET_KEY")
    algorithm: str       = Field("HS256", env="ALGORITHM")
    access_token_expire_minutes: int = Field(30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    debug: bool          = Field(False, env="DEBUG")

    class Config:
        # carrega .env da raiz do projeto
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

settings = Settings()
