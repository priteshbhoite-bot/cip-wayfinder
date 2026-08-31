"""Checks that the local Streamlit theme remains a complete, readable configuration."""

from pathlib import Path
import tomllib


def test_sigmaflow_inspired_theme_declares_the_core_accessible_colors() -> None:
    project_root = Path(__file__).resolve().parents[1]
    with (project_root / ".streamlit" / "config.toml").open("rb") as theme_file:
        theme = tomllib.load(theme_file)["theme"]

    assert theme["base"] == "light"
    assert theme["primaryColor"] == "#006C8F"
    assert theme["blueColor"] == "#006C8F"
    assert theme["greenColor"] == "#0A845F"
    assert theme["backgroundColor"] == "#F9FBFC"
    assert theme["textColor"] == "#102A43"
