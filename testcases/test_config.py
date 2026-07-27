import pytest

import commons.config as config_module


AppConfig = config_module.AppConfig
ConfigManager = config_module.ConfigManager


pytestmark = pytest.mark.unit


def test_parse_bool_uses_explicit_tokens_and_default():
    assert config_module.parse_bool("YES", default=False) is True
    assert config_module.parse_bool("off", default=True) is False
    assert config_module.parse_bool(None, default=True) is True
    assert config_module.parse_bool("unexpected", default=False) is False


def test_app_config_from_env_preserves_defaults(monkeypatch):
    for key in (
        "APPIUM_SERVER_URL",
        "ANDROID_DEVICE_NAME",
        "APP_PACKAGE",
        "APP_ACTIVITY",
        "NO_RESET",
    ):
        monkeypatch.delenv(key, raising=False)

    config = AppConfig.from_env()

    assert config.appium_server_url == "http://localhost:4723"
    assert config.device_name == "P7T4XC99CYAEYL4H"
    assert config.app_package == "com.bs.feifubao"
    assert config.app_activity == "com.bs.feifubao.activity.MainActivity"
    assert config.no_reset is True


def test_app_config_from_env_applies_runtime_overrides(monkeypatch):
    monkeypatch.setenv("APPIUM_SERVER_URL", "http://127.0.0.1:4725/")
    monkeypatch.setenv("ANDROID_DEVICE_NAME", "device-from-env")
    monkeypatch.setenv("APP_PACKAGE", "example.package")
    monkeypatch.setenv("APP_ACTIVITY", ".Main")
    monkeypatch.setenv("NO_RESET", "false")

    config = AppConfig.from_env()

    assert config.appium_server_url == "http://127.0.0.1:4725"
    assert config.device_name == "device-from-env"
    assert config.app_package == "example.package"
    assert config.app_activity == ".Main"
    assert config.no_reset is False


def test_create_config_applies_explicit_kwargs_after_environment(monkeypatch):
    monkeypatch.setenv("ANDROID_DEVICE_NAME", "device-from-env")

    config = ConfigManager().create_config(device_name="explicit-device")

    assert config.device_name == "explicit-device"
