from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """全部配置来自环境变量 / .env（见 .env.example）。"""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # 数据库
    database_url: str = "postgresql+asyncpg://muse:muse@localhost:5432/muse"

    # 存储
    storage_backend: str = "local"  # local | minio
    storage_dir: str = "./data/storage"
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "muse"
    minio_secret_key: str = "muse12345"
    minio_bucket: str = "muse-media"

    # LLM（OpenAI 兼容）
    llm_base_url: str | None = None
    llm_api_key: str | None = None
    llm_model: str = "qwen-vl-max"

    # 企业微信智能机器人（Phase 1）
    wecom_corpid: str | None = None
    wecom_bot_id: str | None = None
    wecom_bot_secret: str | None = None

    # 企业微信会话存档（Phase 2）
    wecom_archive_secret: str | None = None


settings = Settings()
