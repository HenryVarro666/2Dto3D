"""Settings come only from the environment, are validated, and name the offending variable."""

from pathlib import Path

import pytest
from pv3d.config import Settings, SettingsError, is_loopback


def test_defaults_are_local_only_and_bounded():
    settings = Settings.from_env({})
    assert settings.host == "127.0.0.1" and settings.port == 8000
    assert settings.log_level == "INFO" and settings.log_format == "text"
    assert settings.cors_origins == () and not settings.exposes_network
    assert settings.max_pending_jobs == 8 and settings.multiview_timeout_s == 1800
    assert settings.data_dir.is_absolute() and settings.data_dir.name == "runtime"


def test_environment_overrides_are_parsed_and_normalized(tmp_path):
    settings = Settings.from_env(
        {
            "PV3D_HOST": "0.0.0.0",
            "PV3D_PORT": "8443",
            "PV3D_LOG_LEVEL": "debug",
            "PV3D_LOG_FORMAT": "JSON",
            "PV3D_CORS_ORIGINS": "https://a.example, http://localhost:5173,https://a.example",
            "PV3D_DATA_DIR": str(tmp_path / "runtime"),
            "PV3D_DEVICE": "CPU",
            "PV3D_MAX_PENDING_JOBS": "3",
            "PV3D_MULTIVIEW_TIMEOUT_S": "120",
        }
    )
    assert settings.exposes_network and settings.port == 8443
    assert settings.log_level == "DEBUG" and settings.log_format == "json"
    assert settings.cors_origins == ("https://a.example", "http://localhost:5173")
    assert settings.data_dir == (tmp_path / "runtime").resolve() and settings.device == "cpu"
    assert settings.max_pending_jobs == 3 and settings.multiview_timeout_s == 120


@pytest.mark.parametrize(
    ("variable", "value"),
    [
        ("PV3D_PORT", "0"),
        ("PV3D_PORT", "eighty"),
        ("PV3D_PORT", "70000"),
        ("PV3D_LOG_LEVEL", "VERBOSE"),
        ("PV3D_LOG_FORMAT", "xml"),
        ("PV3D_CORS_ORIGINS", "a.example"),
        ("PV3D_DEVICE", "tpu"),
        ("PV3D_MAX_PENDING_JOBS", "0"),
        ("PV3D_MULTIVIEW_TIMEOUT_S", "5"),
    ],
)
def test_invalid_values_fail_fast_and_name_the_variable(variable, value):
    with pytest.raises(SettingsError, match=variable):
        Settings.from_env({variable: value})


def test_blank_values_fall_back_to_defaults():
    settings = Settings.from_env({"PV3D_PORT": "  ", "PV3D_HOST": "", "PV3D_LOG_LEVEL": ""})
    assert settings.port == 8000 and settings.host == "127.0.0.1" and settings.log_level == "INFO"


def test_loopback_detection_covers_names_and_both_ip_families():
    assert all(is_loopback(host) for host in ("127.0.0.1", "127.8.8.8", "::1", "localhost"))
    assert not any(is_loopback(host) for host in ("0.0.0.0", "::", "192.168.1.5", "example.com"))


def test_settings_are_immutable_and_paths_are_path_objects():
    settings = Settings.from_env({})
    assert isinstance(settings.model_dir, Path)
    with pytest.raises(AttributeError):
        settings.port = 1  # type: ignore[misc]
