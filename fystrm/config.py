from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    host: str = "0.0.0.0"
    port: int = 8095
    debug: bool = False
    secret_key: str = "change-me"

    # Database
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_user: str = "fystrm"
    postgres_password: str = "fystrm"
    postgres_db: str = "fystrm"

    # Redis
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_db: int = 0

    # TMDB
    tmdb_api_key: str = ""
    tmdb_language: str = "zh-CN"

    # Emby
    emby_url: str = ""
    emby_api_key: str = ""

    # CD2 Webhook
    cd2_webhook_token: str = ""
    # CD2 在 fystrm 容器内的 FUSE 挂载根, webhook 收到的网盘相对路径会自动拼上此前缀
    cd2_mount_root: str = "/mnt/CloudNAS"

    # Logging
    log_level: str = "INFO"

    @property
    def database_url(self) -> str:
        return f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    @property
    def database_url_sync(self) -> str:
        return f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"


settings = Settings()  # type: ignore[call-arg]
