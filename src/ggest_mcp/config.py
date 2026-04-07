from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Environment-based configuration for the gGest MCP server."""

    model_config = {"env_prefix": "GGEST_", "env_file": ".env"}

    # API host (without protocol or path)
    host: str = "golfinhosoftware.pcscloud.net"

    # API credentials
    username: str
    password: str

    # Database connection — sent to /api/configurarAcessoBD on startup
    db_servidor: str = ""
    db_porta: str = ""
    db_base_dados: str = ""
    db_utilizador: str = ""
    db_password: str = ""

    @property
    def base_url_v1(self) -> str:
        return f"https://{self.host}/api/v1"

    @property
    def base_url_old(self) -> str:
        return f"https://{self.host}/api"


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()  # type: ignore[call-arg]
    return _settings
