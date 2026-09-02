from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: str = Field(default="development")
    app_host: str = Field(default="0.0.0.0")
    app_port: int = Field(default=8001)
    app_cors_origins: str = Field(default="http://localhost:5173")
    api_base_path: str = Field(default="/api")
    public_api_base_url: str = Field(default="http://localhost:8001")
    frontend_base_url: str = Field(default="http://localhost:5173")

    session_secret: str = Field(default="")
    session_cookie_name: str = Field(default="marcopolo_integration_demo_session")
    session_max_age_seconds: int = Field(default=43200)
    session_https_only: bool = Field(default=False)

    auth_required: bool = Field(default=True)
    auth_default_return_url: str = Field(default="http://localhost:5173/")

    marcopolo_mcp_url: str = Field(default="http://localhost:8000")
    marcopolo_api_base_url: str = Field(default="http://localhost:8000/api")
    marcopolo_web_base_url: str = Field(default="http://localhost:8000")
    marcopolo_browser_bootstrap_path: str = Field(default="/api/auth/bootstrap")
    marcopolo_browser_bootstrap_redirect: str = Field(default="/app/")
    marcopolo_developer_api_token: str = Field(default="")
    marcopolo_namespace_key: str = Field(default="")


    llm_provider: str = Field(default="openai")
    llm_model: str = Field(default="gpt-5-mini")
    llm_api_base_url: str = Field(default="https://api.openai.com/v1")
    llm_api_key: str = Field(default="")

    skill_repo_path: str = Field(default="")

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.app_cors_origins.split(",") if origin.strip()]

    @property
    def developer_api_token_configured(self) -> bool:
        return bool(self.marcopolo_developer_api_token.strip())

    @property
    def namespace_key_configured(self) -> bool:
        return bool(self.marcopolo_namespace_key.strip())

    @property
    def marcopolo_auth_mode_effective(self) -> str:
        return "namespace_key"


@lru_cache
def get_settings() -> Settings:
    return Settings()
