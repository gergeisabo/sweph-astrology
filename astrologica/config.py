"""Configuration system for astrologica.

Supports:
  - Custom endpoint URLs (e.g. self-hosted AstroWay, future API)
  - AstroWay as fallback backup
  - Local-only mode (default — no external calls)
"""
from __future__ import annotations
import os
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
EPHE_PATH = str(PROJECT_ROOT / "ephe")


@dataclass
class Config:
    # Local ephemeris settings
    ephe_path: str = EPHE_PATH
    default_ayanamsa: str = "lahiri"
    default_house_system: str = "whole_sign"  # Vedic standard

    # Fallback API (AstroWay backup)
    api_base_url: str = ""  # empty = local-only
    api_key: str = ""
    api_user_agent: str = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    # Interpretation backend (LLM)
    llm_provider: str = ""  # e.g. "minimax", "deepseek", "glm"
    llm_api_key: str = ""

    # Output defaults
    output_dir: str = str(Path.home() / "Projects" / "astrologica" / "output")

    @classmethod
    def from_env(cls) -> Config:
        """Load from environment variables."""
        return cls(
            ephe_path=os.environ.get("ASTROLOGICA_EPHE_PATH", EPHE_PATH),
            default_ayanamsa=os.environ.get("ASTROLOGICA_AYANAMSA", "lahiri"),
            default_house_system=os.environ.get("ASTROLOGICA_HOUSES", "whole_sign"),
            api_base_url=os.environ.get("ASTROWAY_BASE_URL", ""),
            api_key=os.environ.get("ASTROWAY_API_KEY", ""),
            llm_provider=os.environ.get("ASTROLOGICA_LLM_PROVIDER", ""),
            llm_api_key=os.environ.get("ASTROLOGICA_LLM_KEY", ""),
            output_dir=os.environ.get("ASTROLOGICA_OUTPUT", str(Path.home() / "Projects" / "astrologica" / "output")),
        )

    def save(self, path: str | None = None) -> None:
        """Save config to YAML."""
        import yaml  # lazy import
        path = path or str(PROJECT_ROOT / "config.yaml")
        with open(path, "w") as f:
            yaml.dump(self.__dict__, f, default_flow_style=False)


# Global config instance — loaded from env or defaults
_config: Config | None = None


def get_config() -> Config:
    global _config
    if _config is None:
        # Try loading from file
        config_path = PROJECT_ROOT / "config.yaml"
        if config_path.exists():
            import yaml
            with open(config_path) as f:
                data = yaml.safe_load(f)
            _config = Config(**data)
        else:
            _config = Config.from_env()
    return _config
