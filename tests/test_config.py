"""First tests of the project. Run from project root with:  pytest

We test configuration because EVERYTHING depends on it — if config is
broken, every later phase breaks. Testing the foundation first is a habit
worth building on day one.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from ytauto.config import settings


def test_project_root_is_correct():
    """PROJECT_ROOT must be the folder that contains src/."""
    assert (settings.project_root / "src" / "ytauto").is_dir()


def test_settings_have_sane_defaults():
    assert settings.app_env in ("development", "production")
    assert settings.log_level in ("DEBUG", "INFO", "WARNING", "ERROR")
    assert settings.channel_niche  # non-empty string


def test_ensure_dirs_creates_folders():
    settings.ensure_dirs()
    assert settings.data_dir.is_dir()
    assert settings.logs_dir.is_dir()


def test_settings_are_immutable():
    """frozen=True must prevent accidental mutation at runtime."""
    import dataclasses
    import pytest

    with pytest.raises(dataclasses.FrozenInstanceError):
        settings.app_env = "hacked"
