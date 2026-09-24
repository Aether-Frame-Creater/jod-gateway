from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="JOD_", env_file=".env", extra="ignore")

    host: str = "127.0.0.1"
    port: int = 8080
    db_path: str = "./data/jod.db"
    master_key_path: str = "./data/master.key"
    log_level: str = "INFO"


settings = Settings()