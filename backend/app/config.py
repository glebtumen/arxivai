from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Values are read from environment variables / .env automatically by
    # pydantic-settings using the (case-insensitive) field names below.
    database_url: str = "postgresql://archivebot:archivebot@localhost:5432/archivebot"
    openrouter_api_key: str = ""
    openrouter_model: str = "openai/gpt-5.4-nano"
    openrouter_whisper_model: str = "openai/whisper-large-v3"
    site_url: str = "http://localhost:3000"
    site_title: str = "ArchiveBot"
    media_dir: str = "/storage/media"
    web_base_url: str = "http://localhost:3000"
    api_base_url: str = "http://localhost:8000"

    # Optional: path to a Netscape-format cookies.txt exported from a
    # logged-in Instagram browser session. Instagram frequently requires
    # this now for downloads to work. Leave empty to download without auth
    # (works for some public content, fails for a lot of it).
    instagram_cookies_file: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
