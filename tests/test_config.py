"""Tests for config loading."""

from pathlib import Path
from unittest.mock import patch

from kerokero.main import load_config


class TestLoadConfig:
    def test_load_existing_config(self, tmp_path):
        config_file = tmp_path / "config.toml"
        config_file.write_text('[ai]\nwhisper_model = "base"\n\n[recording]\nduration_seconds = 90\n')

        with patch("kerokero.main.CONFIG_PATH", config_file):
            config = load_config()

        assert config["ai"]["whisper_model"] == "base"
        assert config["recording"]["duration_seconds"] == 90

    def test_missing_config_triggers_setup(self, tmp_path):
        kerokero_dir = tmp_path / "kerokero_home"
        config_file = kerokero_dir / "config.toml"
        sessions_dir = kerokero_dir / "sessions"

        with (
            patch("kerokero.main.CONFIG_PATH", config_file),
            patch("kerokero.main.KEROKERO_DIR", kerokero_dir),
            patch("kerokero.main.SESSIONS_DIR", sessions_dir),
            patch("kerokero.main.console") as mock_console,
        ):
            mock_console.input.side_effect = ["tiny", "120", "ja"]
            config = load_config()

        assert config["ai"]["whisper_model"] == "tiny"
        assert config["recording"]["duration_seconds"] == 120
        assert config["display"]["language"] == "ja"
        assert config_file.exists()
