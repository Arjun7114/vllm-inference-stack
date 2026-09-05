"""
Application configuration.

Reads settings from environment variables (with sensible defaults) so the same
code runs locally with a mock backend and in production against real vLLM,
without code changes. Values can be set in a .env file or the real environment.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Which backend to use: "mock" for free local dev, "vllm" for the real thing.
    backend: str = "mock"

    # Where the real vLLM server lives (used only when backend == "vllm").
    vllm_base_url: str = "http://localhost:8000"
    model_name: str = "mistralai/Mistral-7B-Instruct-v0.3"

    # API key clients must present.
    api_key: str = "dev-key-change-me"

    # Guardrails: path to the standalone llm-guardrails-gateway repo. If set and
    # importable, real screening activates; otherwise the app uses passthrough.
    guardrails_gateway_path: str = ""


settings = Settings()


def get_backend():
    """
    Return the backend instance selected by config. This is the single place
    that decides mock vs vllm -- the rest of the app just calls `get_backend()`.
    """
    if settings.backend == "vllm":
        from app.backends.vllm_backend import VLLMBackend
        return VLLMBackend(base_url=settings.vllm_base_url, model_name=settings.model_name)

    from app.backends.mock import MockBackend
    return MockBackend()
