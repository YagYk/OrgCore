import os
from functools import lru_cache
from dotenv import load_dotenv


load_dotenv()


class Settings:
    def __init__(self) -> None:
        self.mongodb_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
        self.master_db_name = os.getenv("MASTER_DB_NAME", "master_db")
        self.jwt_secret_key = os.getenv("JWT_SECRET_KEY", "change-me-in-prod")
        self.jwt_algorithm = os.getenv("JWT_ALGORITHM", "HS256")
        self.jwt_expires_minutes = int(os.getenv("JWT_EXPIRES_MINUTES", "60"))


@lru_cache
def get_settings() -> Settings:
    return Settings()

