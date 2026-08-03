"""Load and validate ~/.czarchive.toml configuration."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

CONFIG_PATH = Path.home() / ".czarchive.toml"

DEFAULT_CONFIG = """\
station = "KSER"
show_name = "Convergence Zone"
output_dir = "~/shows"

# Mixcloud (required for upload)
mixcloud_client_id = ""
mixcloud_client_secret = ""
mixcloud_access_token = ""   # populated by `czarchive auth`

# Spinitron API key (optional — leave blank to use scraping)
spinitron_api_key = ""
"""


@dataclass
class Config:
    station: str = "KSER"
    show_name: str = "Convergence Zone"
    output_dir: Path = field(default_factory=lambda: Path.home() / "shows")
    mixcloud_client_id: str = ""
    mixcloud_client_secret: str = ""
    mixcloud_access_token: str = ""
    spinitron_api_key: str = ""

    @property
    def output_path(self) -> Path:
        return Path(self.output_dir).expanduser()


def load_config(path: Path = CONFIG_PATH) -> Config:
    """Load config from TOML file, creating default if missing."""
    if not path.exists():
        path.write_text(DEFAULT_CONFIG)
        print(f"Created default config at {path} — please fill in credentials.")

    with open(path, "rb") as f:
        data = tomllib.load(f)

    output_dir = Path(data.get("output_dir", "~/shows")).expanduser()
    return Config(
        station=data.get("station", "KSER"),
        show_name=data.get("show_name", "Convergence Zone"),
        output_dir=output_dir,
        mixcloud_client_id=data.get("mixcloud_client_id", ""),
        mixcloud_client_secret=data.get("mixcloud_client_secret", ""),
        mixcloud_access_token=data.get("mixcloud_access_token", ""),
        spinitron_api_key=data.get("spinitron_api_key", ""),
    )


def save_token(access_token: str, path: Path = CONFIG_PATH) -> None:
    """Update mixcloud_access_token in the config file in-place."""
    text = path.read_text()
    lines = text.splitlines()
    new_lines = []
    replaced = False
    for line in lines:
        if line.strip().startswith("mixcloud_access_token"):
            new_lines.append(f'mixcloud_access_token = "{access_token}"')
            replaced = True
        else:
            new_lines.append(line)
    if not replaced:
        new_lines.append(f'mixcloud_access_token = "{access_token}"')
    path.write_text("\n".join(new_lines) + "\n")
