# Foundation Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Safely back up and remove confirmed legacy artifacts, restore a runnable offline test baseline, and consolidate configuration, Android launch, driver, logging, waiting, and failure-diagnostic primitives without changing business flows or public entry points.

**Architecture:** Stage 0 creates a verified external backup before any deletion. Stage 1 introduces focused modules under `commons`, keeps compatibility wrappers for existing imports, and proves each behavior with offline tests before implementation. Domain page objects and flows consume the new primitives only in later domain-specific plans.

**Tech Stack:** Python 3.11.9, pytest 8.3.5, Selenium 4.41.0, Appium-Python-Client 5.2.7, PowerShell, Appium 3.2.0.

## Global Constraints

- The current Git repository is the only source of truth for business flow and structure.
- Preserve existing public classes, method names, imports, default values, and no-side-effect defaults.
- Do not submit orders, pay, send verification codes, or add, edit, or delete business data.
- Never write account numbers, passwords, verification codes, payment data, or real personal data to source, tests, docs, artifact names, screenshots, or logs.
- Create and verify `C:\Users\18718\Desktop\appium_project\venv\backups\20260722_before_refactor.zip` before deleting any approved artifact.
- Keep `C:\Users\18718\Desktop\appium_project\venv\pyvenv.cfg` unchanged.
- Run every production-code change through a failing test first.
- The current shell cannot locate `git`; do not claim a commit unless a fresh `git` command succeeds.
- Real-device validation is deferred to the final repository validation stage; this plan runs offline tests and read-only environment checks only.

---

## File Structure

- Create `pytest.ini`: real pytest configuration replacing the accidental directory of the same name.
- Create `commons/android_runtime.py`: ADB discovery, launchable-activity resolution, and post-session App launch policy.
- Modify `commons/config.py`: environment-aware immutable defaults while preserving `AppConfig`, `ConfigManager`, `get_default_config`, and `create_config`.
- Modify `commons/driver.py`: delegate Android launch behavior, make session lifecycle deterministic, and keep `DriverManager` API compatibility.
- Modify `commons/logger.py`: one managed handler set, one process log file, UTF-8 output, and keyed-secret redaction.
- Modify `pages/app_common.py`: compatibility adapter that re-exports the shared logger and delegates device/activity detection.
- Create `commons/waits.py`: monotonic condition polling and optional/required element lookup primitives.
- Create `commons/diagnostics.py`: sanitized screenshot and page-source capture on failure.
- Create `testcases/test_config.py`: configuration and environment precedence tests.
- Create `testcases/test_android_runtime.py`: ADB parsing and launch-mode tests.
- Create `testcases/test_driver.py`: DriverManager cache, implicit-wait, failure, and close tests.
- Create `testcases/test_logger.py`: duplicate-handler and secret-redaction tests.
- Create `testcases/test_waits.py`: deterministic polling tests.
- Create `testcases/test_diagnostics.py`: artifact creation and sanitization tests.
- Modify `testcases/test_login.py`: mark the existing live-device module as `device` without changing its flow.

---

### Task 1: Verified Backup and Approved Cleanup

**Files:**
- Create outside repo: `C:\Users\18718\Desktop\appium_project\venv\backups\20260722_before_refactor.zip`
- Delete after verification: `C:\Users\18718\Desktop\appium_project\venv\test.py`
- Delete after verification: `C:\Users\18718\Desktop\appium_project\venv\generate_pay_testcases_xlsx.py`
- Delete after verification: `C:\Users\18718\Desktop\appium_project\venv\chopsticks_robust_20260319_152034.log`
- Delete after verification: `.pytest_cache/`
- Delete after verification: `.superpowers/sdd/`
- Delete after verification: `pytest.ini/`
- Delete after verification: `testcases tree/`
- Delete after verification: `tmp/`
- Delete after verification: `logs/*.log`
- Preserve: `logs/shipping_new_user_guide.png`
- Preserve: `C:\Users\18718\Desktop\appium_project\venv\pyvenv.cfg`

**Interfaces:**
- Consumes: the exact approved source paths and the repository root.
- Produces: a readable ZIP containing `manifest.csv`, hashes, and all cleanup targets; original approved targets removed only after validation.

- [ ] **Step 1: Resolve and validate every destructive target**

Run from the repository root in one PowerShell process:

```powershell
$repoRoot = (Resolve-Path '.').Path
$venvRoot = (Resolve-Path '..').Path
$expectedRepo = 'C:\Users\18718\Desktop\appium_project\venv\kuaizishenghuo'
$expectedVenv = 'C:\Users\18718\Desktop\appium_project\venv'
if ($repoRoot -ne $expectedRepo) { throw "Unexpected repo root: $repoRoot" }
if ($venvRoot -ne $expectedVenv) { throw "Unexpected venv root: $venvRoot" }

$requiredFiles = @(
  (Join-Path $venvRoot 'test.py'),
  (Join-Path $venvRoot 'generate_pay_testcases_xlsx.py'),
  (Join-Path $venvRoot 'chopsticks_robust_20260319_152034.log'),
  (Join-Path $venvRoot 'pyvenv.cfg')
)
$missing = $requiredFiles | Where-Object { -not (Test-Path -LiteralPath $_ -PathType Leaf) }
if ($missing) { throw "Missing required paths: $($missing -join ', ')" }

$repoDirs = @('.pytest_cache', '.superpowers\sdd', 'pytest.ini', 'testcases tree', 'tmp')
foreach ($relative in $repoDirs) {
  $candidate = [IO.Path]::GetFullPath((Join-Path $repoRoot $relative))
  if (-not $candidate.StartsWith($repoRoot + [IO.Path]::DirectorySeparatorChar)) {
    throw "Target escapes repository: $candidate"
  }
}
```

Expected: exit code `0`; no missing-path or path-escape error. `pyvenv.cfg` is checked but never added to the deletion list.

- [ ] **Step 2: Build a staging copy and SHA-256 manifest**

Run with approval because the backup target is outside the writable repository root:

```powershell
$repoRoot = (Resolve-Path '.').Path
$venvRoot = (Resolve-Path '..').Path
$backupRoot = Join-Path $venvRoot 'backups'
$staging = Join-Path $env:TEMP 'chopsticks_refactor_backup_20260722'
$zipPath = Join-Path $backupRoot '20260722_before_refactor.zip'

if (Test-Path -LiteralPath $staging) { Remove-Item -LiteralPath $staging -Recurse -Force }
New-Item -ItemType Directory -Path $staging | Out-Null
New-Item -ItemType Directory -Path $backupRoot -Force | Out-Null

Copy-Item -LiteralPath (Join-Path $venvRoot 'test.py') -Destination (Join-Path $staging 'legacy_test.py')
Copy-Item -LiteralPath (Join-Path $venvRoot 'generate_pay_testcases_xlsx.py') -Destination (Join-Path $staging 'generate_pay_testcases_xlsx.py')
Copy-Item -LiteralPath (Join-Path $venvRoot 'chopsticks_robust_20260319_152034.log') -Destination (Join-Path $staging 'chopsticks_robust_20260319_152034.log')

$repoBackup = Join-Path $staging 'repository_artifacts'
New-Item -ItemType Directory -Path $repoBackup | Out-Null
foreach ($relative in @('.pytest_cache', '.superpowers\sdd', 'pytest.ini', 'testcases tree', 'tmp', 'logs')) {
  $source = Join-Path $repoRoot $relative
  if (Test-Path -LiteralPath $source) {
    $destination = Join-Path $repoBackup $relative
    $parent = Split-Path -Parent $destination
    New-Item -ItemType Directory -Path $parent -Force | Out-Null
    Copy-Item -LiteralPath $source -Destination $destination -Recurse -Force
  }
}

Get-ChildItem -LiteralPath $staging -Recurse -File |
  Where-Object Name -ne 'manifest.csv' |
  ForEach-Object {
    [PSCustomObject]@{
      RelativePath = $_.FullName.Substring($staging.Length + 1)
      Length = $_.Length
      SHA256 = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash
    }
  } | Export-Csv -LiteralPath (Join-Path $staging 'manifest.csv') -NoTypeInformation -Encoding UTF8

if (Test-Path -LiteralPath $zipPath) { throw "Backup already exists: $zipPath" }
Compress-Archive -Path (Join-Path $staging '*') -DestinationPath $zipPath -CompressionLevel Optimal
```

Expected: exit code `0`; ZIP and manifest are created without overwriting an older backup.

- [ ] **Step 3: Independently open the ZIP and compare hashes**

```powershell
$venvRoot = (Resolve-Path '..').Path
$zipPath = Join-Path $venvRoot 'backups\20260722_before_refactor.zip'
$verifyDir = Join-Path $env:TEMP 'chopsticks_refactor_verify_20260722'
if (Test-Path -LiteralPath $verifyDir) { Remove-Item -LiteralPath $verifyDir -Recurse -Force }
Expand-Archive -LiteralPath $zipPath -DestinationPath $verifyDir
$manifest = Import-Csv -LiteralPath (Join-Path $verifyDir 'manifest.csv')
if (-not $manifest) { throw 'Backup manifest is empty' }
foreach ($entry in $manifest) {
  $path = Join-Path $verifyDir $entry.RelativePath
  if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "Missing backup file: $($entry.RelativePath)" }
  $actual = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash
  if ($actual -ne $entry.SHA256) { throw "Hash mismatch: $($entry.RelativePath)" }
}
$required = @('legacy_test.py', 'generate_pay_testcases_xlsx.py', 'chopsticks_robust_20260319_152034.log')
foreach ($name in $required) {
  if (-not (Test-Path -LiteralPath (Join-Path $verifyDir $name))) { throw "Required backup entry missing: $name" }
}
[PSCustomObject]@{ Zip=$zipPath; Entries=$manifest.Count; SHA256=(Get-FileHash -LiteralPath $zipPath -Algorithm SHA256).Hash }
```

Expected: exit code `0`; every manifest entry exists and matches its stored hash.

- [ ] **Step 4: Delete only the approved originals**

Run with approval because three targets are outside the repository and deletion is destructive:

```powershell
$repoRoot = (Resolve-Path '.').Path
$venvRoot = (Resolve-Path '..').Path
if ($repoRoot -ne 'C:\Users\18718\Desktop\appium_project\venv\kuaizishenghuo') { throw 'Repository root changed' }
if ($venvRoot -ne 'C:\Users\18718\Desktop\appium_project\venv') { throw 'Venv root changed' }

foreach ($path in @(
  (Join-Path $venvRoot 'test.py'),
  (Join-Path $venvRoot 'generate_pay_testcases_xlsx.py'),
  (Join-Path $venvRoot 'chopsticks_robust_20260319_152034.log')
)) {
  Remove-Item -LiteralPath $path -Force
}

foreach ($relative in @('.pytest_cache', '.superpowers\sdd', 'pytest.ini', 'testcases tree', 'tmp')) {
  $path = [IO.Path]::GetFullPath((Join-Path $repoRoot $relative))
  if (-not $path.StartsWith($repoRoot + [IO.Path]::DirectorySeparatorChar)) { throw "Unsafe path: $path" }
  if (Test-Path -LiteralPath $path) { Remove-Item -LiteralPath $path -Recurse -Force }
}

$logsRoot = [IO.Path]::GetFullPath((Join-Path $repoRoot 'logs'))
$logFiles = Get-ChildItem -LiteralPath $logsRoot -File -Filter '*.log'
foreach ($file in $logFiles) {
  if (-not $file.FullName.StartsWith($logsRoot + [IO.Path]::DirectorySeparatorChar)) { throw "Unsafe log path: $($file.FullName)" }
  Remove-Item -LiteralPath $file.FullName -Force
}
```

Expected: exit code `0`; `logs/shipping_new_user_guide.png` and `pyvenv.cfg` remain.

- [ ] **Step 5: Verify cleanup and recovery instructions**

```powershell
$repoRoot = (Resolve-Path '.').Path
$venvRoot = (Resolve-Path '..').Path
$deleted = @(
  (Join-Path $venvRoot 'test.py'),
  (Join-Path $venvRoot 'generate_pay_testcases_xlsx.py'),
  (Join-Path $venvRoot 'chopsticks_robust_20260319_152034.log'),
  (Join-Path $repoRoot '.pytest_cache'),
  (Join-Path $repoRoot '.superpowers\sdd'),
  (Join-Path $repoRoot 'pytest.ini'),
  (Join-Path $repoRoot 'testcases tree'),
  (Join-Path $repoRoot 'tmp')
)
$remaining = $deleted | Where-Object { Test-Path -LiteralPath $_ }
if ($remaining) { throw "Cleanup targets remain: $($remaining -join ', ')" }
if (-not (Test-Path -LiteralPath (Join-Path $venvRoot 'pyvenv.cfg'))) { throw 'pyvenv.cfg was removed' }
if (-not (Test-Path -LiteralPath (Join-Path $repoRoot 'logs\shipping_new_user_guide.png'))) { throw 'Required PNG was removed' }
Write-Output 'Recovery: Expand-Archive ..\backups\20260722_before_refactor.zip to a temporary directory and restore selected files from its manifest.'
```

Expected: exit code `0` and a recovery instruction line.

- [ ] **Step 6: Record commit when Git is available**

```powershell
git add -A .pytest_cache .superpowers/sdd pytest.ini "testcases tree" tmp logs
git commit -m "chore: archive obsolete automation artifacts"
```

Expected: commit succeeds. If `git` remains unavailable, record `未提交：git 不可用` and do not claim otherwise.

---

### Task 2: Restore the Offline Pytest Baseline

**Files:**
- Create: `pytest.ini`
- Modify: `testcases/test_login.py`
- Verify: `requirements.txt`

**Interfaces:**
- Consumes: pytest 8.3.5 and existing `testcases` modules.
- Produces: markers `unit` and `device`; default collection under `testcases`; offline selection command `python -m pytest -m "not device"`.

- [ ] **Step 1: Install the declared requirements**

Run with network/write approval if the sandbox blocks package installation:

```powershell
& '..\Scripts\python.exe' -m pip install -r requirements.txt
```

Expected: exit code `0`; `pytest==8.3.5` and `allure-pytest==2.15.0` are installed.

- [ ] **Step 2: Create pytest configuration and mark the live-device module**

Create `pytest.ini` with:

```ini
[pytest]
testpaths = testcases
python_files = test_*.py
addopts = -ra
markers =
    unit: offline deterministic test with no Appium session
    device: requires a connected Android device and Appium server
```

Add below the imports in `testcases/test_login.py`:

```python
pytestmark = pytest.mark.device
```

- [ ] **Step 3: Run collection and offline baseline**

```powershell
& '..\Scripts\python.exe' -m pytest --collect-only -q
& '..\Scripts\python.exe' -m pytest -m 'not device' -q
```

Expected: collection succeeds. Record the exact baseline pass/fail counts; existing failures are evidence for later tasks and must not be hidden by changing assertions.

- [ ] **Step 4: Commit**

```powershell
git add pytest.ini testcases/test_login.py requirements.txt
git commit -m "test: restore offline pytest baseline"
```

Expected: commit succeeds, or record `未提交：git 不可用`.

---

### Task 3: Environment-Aware Configuration with Compatible Defaults

**Files:**
- Modify: `commons/config.py`
- Create: `testcases/test_config.py`

**Interfaces:**
- Consumes: `os.environ`, `UiAutomator2Options`.
- Produces: `parse_bool(value: str | None, default: bool) -> bool`, `AppConfig.from_env() -> AppConfig`, existing `AppConfig.get_desired_caps()`, existing `AppConfig.get_uiautomator2_options()`, existing `ConfigManager.get_default_config()`, existing `ConfigManager.create_config(**kwargs)`.

- [ ] **Step 1: Write failing configuration tests**

Create `testcases/test_config.py`:

```python
import pytest

from commons.config import AppConfig, ConfigManager, parse_bool


pytestmark = pytest.mark.unit


def test_parse_bool_uses_explicit_tokens_and_default():
    assert parse_bool('YES', default=False) is True
    assert parse_bool('off', default=True) is False
    assert parse_bool(None, default=True) is True
    assert parse_bool('unexpected', default=False) is False


def test_app_config_from_env_preserves_defaults(monkeypatch):
    for key in ('APPIUM_SERVER_URL', 'ANDROID_DEVICE_NAME', 'APP_PACKAGE', 'APP_ACTIVITY', 'NO_RESET'):
        monkeypatch.delenv(key, raising=False)
    config = AppConfig.from_env()
    assert config.appium_server_url == 'http://localhost:4723'
    assert config.device_name == 'P7T4XC99CYAEYL4H'
    assert config.app_package == 'com.bs.feifubao'
    assert config.app_activity == 'com.bs.feifubao.activity.MainActivity'
    assert config.no_reset is True


def test_app_config_from_env_applies_runtime_overrides(monkeypatch):
    monkeypatch.setenv('APPIUM_SERVER_URL', 'http://127.0.0.1:4725/')
    monkeypatch.setenv('ANDROID_DEVICE_NAME', 'device-from-env')
    monkeypatch.setenv('APP_PACKAGE', 'example.package')
    monkeypatch.setenv('APP_ACTIVITY', '.Main')
    monkeypatch.setenv('NO_RESET', 'false')
    config = AppConfig.from_env()
    assert config.appium_server_url == 'http://127.0.0.1:4725'
    assert config.device_name == 'device-from-env'
    assert config.app_package == 'example.package'
    assert config.app_activity == '.Main'
    assert config.no_reset is False


def test_create_config_applies_explicit_kwargs_after_environment(monkeypatch):
    monkeypatch.setenv('ANDROID_DEVICE_NAME', 'device-from-env')
    config = ConfigManager().create_config(device_name='explicit-device')
    assert config.device_name == 'explicit-device'
```

- [ ] **Step 2: Run tests to verify RED**

```powershell
& '..\Scripts\python.exe' -m pytest testcases/test_config.py -q
```

Expected: FAIL because `parse_bool` and `AppConfig.from_env` do not exist and `appium_server_url` is not environment-backed.

- [ ] **Step 3: Implement the minimal compatible configuration**

Replace `commons/config.py` with:

```python
"""Typed Appium configuration with environment overrides."""

from __future__ import annotations

import os
from dataclasses import dataclass, replace

from appium.options.android import UiAutomator2Options


TRUE_VALUES = frozenset({'1', 'true', 'yes', 'y', 'on'})
FALSE_VALUES = frozenset({'0', 'false', 'no', 'n', 'off'})


def parse_bool(value: str | None, *, default: bool) -> bool:
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in TRUE_VALUES:
        return True
    if normalized in FALSE_VALUES:
        return False
    return default


@dataclass(frozen=True)
class DeviceConfig:
    platform_name: str = 'Android'
    automation_name: str = 'UiAutomator2'
    device_name: str = 'P7T4XC99CYAEYL4H'
    no_reset: bool = True
    unicode_keyboard: bool = True
    reset_keyboard: bool = True
    new_command_timeout: int = 300
    appium_server_url: str = 'http://localhost:4723'


@dataclass(frozen=True)
class AppConfig(DeviceConfig):
    app_package: str = 'com.bs.feifubao'
    app_activity: str = 'com.bs.feifubao.activity.MainActivity'

    @classmethod
    def from_env(cls) -> 'AppConfig':
        defaults = cls()
        return cls(
            appium_server_url=os.environ.get('APPIUM_SERVER_URL', defaults.appium_server_url).rstrip('/'),
            device_name=os.environ.get('ANDROID_DEVICE_NAME', defaults.device_name).strip() or defaults.device_name,
            app_package=os.environ.get('APP_PACKAGE', defaults.app_package).strip() or defaults.app_package,
            app_activity=os.environ.get('APP_ACTIVITY', defaults.app_activity).strip() or defaults.app_activity,
            no_reset=parse_bool(os.environ.get('NO_RESET'), default=defaults.no_reset),
        )

    def get_desired_caps(self) -> dict:
        return {
            'platformName': self.platform_name,
            'deviceName': self.device_name,
            'appPackage': self.app_package,
            'appActivity': self.app_activity,
            'noReset': self.no_reset,
            'unicodeKeyboard': self.unicode_keyboard,
            'resetKeyboard': self.reset_keyboard,
            'automationName': self.automation_name,
            'newCommandTimeout': self.new_command_timeout,
        }

    def get_uiautomator2_options(self) -> UiAutomator2Options:
        options = UiAutomator2Options()
        for key, value in self.get_desired_caps().items():
            options.set_capability(key, value)
        options.set_capability('appium:chromedriverAutodownload', True)
        options.set_capability('appium:autoWebview', False)
        options.set_capability('appium:ensureWebviewsHavePages', True)
        return options


class ConfigManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def get_default_config(self) -> AppConfig:
        return AppConfig.from_env()

    def create_config(self, **kwargs) -> AppConfig:
        config = self.get_default_config()
        known = {key: value for key, value in kwargs.items() if hasattr(config, key)}
        return replace(config, **known)
```

- [ ] **Step 4: Run configuration tests and existing offline tests**

```powershell
& '..\Scripts\python.exe' -m pytest testcases/test_config.py -q
& '..\Scripts\python.exe' -m pytest -m 'not device' -q
```

Expected: configuration tests PASS; no existing offline baseline regression.

- [ ] **Step 5: Commit**

```powershell
git add commons/config.py testcases/test_config.py
git commit -m "refactor: centralize runtime configuration"
```

Expected: commit succeeds, or record `未提交：git 不可用`.

---

### Task 4: Shared Android Runtime Policy

**Files:**
- Create: `commons/android_runtime.py`
- Modify: `commons/driver.py`
- Modify: `pages/app_common.py`
- Create: `testcases/test_android_runtime.py`

**Interfaces:**
- Consumes: `subprocess.run`, an Appium driver, and `AppConfig`.
- Produces: `detect_first_adb_device_id(run=subprocess.run) -> str | None`, `detect_launchable_activity(app_package: str, run=subprocess.run) -> str | None`, `post_session_android_launch(driver, config: AppConfig, start_mode: str | None = None) -> str`.
- Compatibility: `commons.driver._detect_launchable_activity` remains importable as an alias; `pages.app_common.AppConfig._detect_first_adb_device_id` and `_detect_launchable_activity` delegate to shared functions.

- [ ] **Step 1: Write failing Android runtime tests**

Create `testcases/test_android_runtime.py` with fake completed processes and a recording driver. Cover these exact cases:

```python
from types import SimpleNamespace

import pytest

from commons.android_runtime import (
    detect_first_adb_device_id,
    detect_launchable_activity,
    post_session_android_launch,
)
from commons.config import AppConfig


pytestmark = pytest.mark.unit


def test_detect_first_adb_device_id_returns_first_ready_device():
    def run(*args, **kwargs):
        return SimpleNamespace(returncode=0, stdout='List of devices attached\nserial-1 device\nserial-2 offline\n')
    assert detect_first_adb_device_id(run=run) == 'serial-1'


def test_detect_launchable_activity_expands_relative_activity():
    def run(*args, **kwargs):
        return SimpleNamespace(returncode=0, stdout='com.example/.MainActivity\n')
    assert detect_launchable_activity('com.example', run=run) == 'com.example.MainActivity'


class RecordingDriver:
    def __init__(self):
        self.calls = []
    def terminate_app(self, package):
        self.calls.append(('terminate', package))
    def start_activity(self, package, activity):
        self.calls.append(('start', package, activity))
    def activate_app(self, package):
        self.calls.append(('activate', package))


def test_post_session_launch_cold_terminates_then_starts():
    driver = RecordingDriver()
    mode = post_session_android_launch(driver, AppConfig(), start_mode='cold')
    assert mode == 'cold'
    assert driver.calls == [
        ('terminate', 'com.bs.feifubao'),
        ('start', 'com.bs.feifubao', 'com.bs.feifubao.activity.MainActivity'),
    ]


def test_post_session_launch_off_has_no_side_effect():
    driver = RecordingDriver()
    assert post_session_android_launch(driver, AppConfig(), start_mode='off') == 'off'
    assert driver.calls == []
```

- [ ] **Step 2: Run tests to verify RED**

```powershell
& '..\Scripts\python.exe' -m pytest testcases/test_android_runtime.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'commons.android_runtime'`.

- [ ] **Step 3: Implement shared detection and launch policy**

Create `commons/android_runtime.py`:

```python
"""Android device discovery and post-session launch policy."""

from __future__ import annotations

import os
import subprocess
from collections.abc import Callable
from typing import Any

from commons.logger import setup_logger


logger = setup_logger(__name__)


def detect_first_adb_device_id(
    run: Callable[..., Any] = subprocess.run,
) -> str | None:
    try:
        completed = run(
            ['adb', 'devices'], capture_output=True, text=True, timeout=8
        )
    except Exception as exc:
        logger.debug('adb devices failed error_type=%s', type(exc).__name__)
        return None
    if completed.returncode != 0:
        return None
    lines = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
    for line in lines[1:]:
        parts = line.split()
        if len(parts) >= 2 and parts[1] == 'device':
            return parts[0]
    return None


def detect_launchable_activity(
    app_package: str,
    run: Callable[..., Any] = subprocess.run,
) -> str | None:
    try:
        completed = run(
            ['adb', 'shell', 'cmd', 'package', 'resolve-activity', '--brief', app_package],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except Exception as exc:
        logger.debug('resolve activity failed error_type=%s', type(exc).__name__)
        return None
    if completed.returncode != 0:
        return None
    lines = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
    if not lines or '/' not in lines[-1]:
        return None
    package, activity = lines[-1].split('/', 1)
    if not package or not activity:
        return None
    return f'{package}{activity}' if activity.startswith('.') else activity


def post_session_android_launch(driver, config, start_mode=None):
    raw_mode = start_mode if start_mode is not None else os.environ.get('START_MODE', 'cold')
    normalized = (raw_mode or 'cold').strip().lower()
    if normalized in {'off', 'none', 'skip', '0', 'false', 'no'}:
        return 'off'
    if normalized == 'activate':
        driver.activate_app(config.app_package)
        return 'activate'
    try:
        driver.terminate_app(config.app_package)
    except Exception as exc:
        logger.debug('terminate_app failed error_type=%s', type(exc).__name__)
    if config.app_activity:
        driver.start_activity(config.app_package, config.app_activity)
    else:
        activity = detect_launchable_activity(config.app_package)
        if activity:
            driver.start_activity(config.app_package, activity)
        else:
            driver.activate_app(config.app_package)
    return 'cold'
```

- [ ] **Step 4: Add compatibility delegation**

In `commons/driver.py`, import the three shared functions, define:

```python
_detect_launchable_activity = detect_launchable_activity
_post_session_android_launch = post_session_android_launch
```

In `pages/app_common.py`, replace its local logger factory with:

```python
from commons.logger import setup_logger
from commons.android_runtime import detect_first_adb_device_id, detect_launchable_activity
```

Keep `pages.app_common.AppConfig` and its existing constants. Its two static methods delegate directly:

```python
_detect_first_adb_device_id = staticmethod(detect_first_adb_device_id)
_detect_launchable_activity = staticmethod(detect_launchable_activity)
```

- [ ] **Step 5: Run focused and offline regression tests**

```powershell
& '..\Scripts\python.exe' -m pytest testcases/test_android_runtime.py testcases/test_config.py -q
& '..\Scripts\python.exe' -m pytest -m 'not device' -q
```

Expected: focused tests PASS and no offline baseline regression.

- [ ] **Step 6: Commit**

```powershell
git add commons/android_runtime.py commons/driver.py pages/app_common.py testcases/test_android_runtime.py
git commit -m "refactor: share Android runtime policy"
```

Expected: commit succeeds, or record `未提交：git 不可用`.

---

### Task 5: Deterministic Driver Session Lifecycle

**Files:**
- Modify: `commons/driver.py`
- Create: `testcases/test_driver.py`

**Interfaces:**
- Consumes: `ConfigManager`, `webdriver.Remote`, `post_session_android_launch`.
- Produces: existing singleton `DriverManager`, `get_driver(session_name: str = 'default', **kwargs)`, `close_driver(session_name: str = 'default')`, `close_all_drivers()`.

- [ ] **Step 1: Write failing lifecycle tests**

Create `testcases/test_driver.py` using a fake driver and monkeypatches. Assert:

```python
import pytest

import commons.driver as driver_module
from commons.driver import DriverManager


pytestmark = pytest.mark.unit


class FakeDriver:
    def __init__(self):
        self.waits = []
        self.quit_calls = 0
    def implicitly_wait(self, value):
        self.waits.append(value)
    def quit(self):
        self.quit_calls += 1


@pytest.fixture(autouse=True)
def reset_manager():
    original = DriverManager._drivers
    DriverManager._drivers = {}
    yield
    DriverManager._drivers = original


def test_get_driver_caches_session_and_disables_implicit_wait(monkeypatch):
    fake = FakeDriver()
    monkeypatch.setattr(driver_module.webdriver, 'Remote', lambda **kwargs: fake)
    monkeypatch.setattr(driver_module, 'post_session_android_launch', lambda driver, config: 'off')
    manager = DriverManager()
    assert manager.get_driver('unit') is fake
    assert manager.get_driver('unit') is fake
    assert fake.waits == [0]


def test_failed_creation_is_not_cached(monkeypatch):
    def fail(**kwargs):
        raise RuntimeError('session failed')
    monkeypatch.setattr(driver_module.webdriver, 'Remote', fail)
    with pytest.raises(RuntimeError, match='session failed'):
        DriverManager().get_driver('broken')
    assert 'broken' not in DriverManager._drivers


def test_close_driver_quits_once_and_clears_session(monkeypatch):
    fake = FakeDriver()
    DriverManager._drivers['unit'] = fake
    manager = DriverManager()
    manager.close_driver('unit')
    manager.close_driver('unit')
    assert fake.quit_calls == 1
    assert DriverManager._drivers['unit'] is None
```

- [ ] **Step 2: Run tests to verify RED**

```powershell
& '..\Scripts\python.exe' -m pytest testcases/test_driver.py -q
```

Expected: at least `test_get_driver_caches_session_and_disables_implicit_wait` FAILS because current code sets implicit wait to `1`.

- [ ] **Step 3: Implement the minimal lifecycle change**

Replace `commons/driver.py` with:

```python
"""Thread-safe Appium driver session management."""

from __future__ import annotations

import threading

from appium import webdriver

from commons.android_runtime import (
    detect_launchable_activity,
    post_session_android_launch,
)
from commons.config import ConfigManager
from commons.logger import setup_logger


logger = setup_logger(__name__)

# Compatibility for existing imports and tests.
_detect_launchable_activity = detect_launchable_activity
_post_session_android_launch = post_session_android_launch


class DriverManager:
    """Cache Appium drivers by explicit session name."""

    _instance = None
    _lock = threading.Lock()
    _drivers: dict[str, object | None] = {}

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def get_driver(self, session_name: str = 'default', **kwargs):
        existing = self._drivers.get(session_name)
        if existing is not None:
            return existing

        config_manager = ConfigManager()
        config = (
            config_manager.create_config(**kwargs)
            if kwargs
            else config_manager.get_default_config()
        )
        logger.info('创建新的驱动实例: %s', session_name)
        try:
            driver = webdriver.Remote(
                command_executor=config.appium_server_url,
                options=config.get_uiautomator2_options(),
            )
            post_session_android_launch(driver, config)
            driver.implicitly_wait(0)
        except Exception:
            self._drivers.pop(session_name, None)
            logger.exception('创建驱动失败 session=%s', session_name)
            raise

        self._drivers[session_name] = driver
        logger.info('驱动实例 %s 创建成功', session_name)
        return driver

    def close_driver(self, session_name: str = 'default') -> None:
        driver = self._drivers.get(session_name)
        if driver is None:
            return
        try:
            driver.quit()
        except Exception as exc:
            logger.warning(
                '关闭驱动时出错 session=%s error_type=%s',
                session_name,
                type(exc).__name__,
            )
        finally:
            self._drivers[session_name] = None

    def close_all_drivers(self) -> None:
        for session_name in list(self._drivers):
            self.close_driver(session_name)
```

- [ ] **Step 4: Run focused and offline tests**

```powershell
& '..\Scripts\python.exe' -m pytest testcases/test_driver.py testcases/test_transfer_cli.py -q
& '..\Scripts\python.exe' -m pytest -m 'not device' -q
```

Expected: focused tests PASS and the transfer CLI tests continue to pass with the existing `_drivers` compatibility contract.

- [ ] **Step 5: Commit**

```powershell
git add commons/driver.py testcases/test_driver.py
git commit -m "refactor: make driver sessions deterministic"
```

Expected: commit succeeds, or record `未提交：git 不可用`.

---

### Task 6: Managed UTF-8 Logging and Keyed-Secret Redaction

**Files:**
- Modify: `commons/logger.py`
- Create: `testcases/test_logger.py`

**Interfaces:**
- Consumes: `logging`, `CHOPSTICKLIFE_LOG_FILE_TAG`, optional `CHOPSTICKLIFE_LOG_DIR`.
- Produces: existing `setup_logger(name=None, log_level=logging.INFO) -> logging.Logger`, new `redact_text(value: object) -> str`.

- [ ] **Step 1: Write failing logging tests**

Create `testcases/test_logger.py`:

```python
import logging

import pytest

import commons.logger as logger_module


pytestmark = pytest.mark.unit


def reset_logger_state():
    logger_module._log_file_path_cache = None
    for name in ('unit.logger', 'unit.logger.second'):
        logger = logging.getLogger(name)
        for handler in list(logger.handlers):
            handler.close()
            logger.removeHandler(handler)


def test_setup_logger_is_idempotent(tmp_path, monkeypatch):
    reset_logger_state()
    monkeypatch.setenv('CHOPSTICKLIFE_LOG_DIR', str(tmp_path))
    first = logger_module.setup_logger('unit.logger')
    second = logger_module.setup_logger('unit.logger')
    assert first is second
    assert len([h for h in first.handlers if getattr(h, '_chopsticks_managed', False)]) == 2


def test_logger_redacts_keyed_secrets(tmp_path, monkeypatch):
    reset_logger_state()
    monkeypatch.setenv('CHOPSTICKLIFE_LOG_DIR', str(tmp_path))
    logger = logger_module.setup_logger('unit.logger.second')
    logger.error('password=secret-value verification_code: 123456 token=abc')
    for handler in logger.handlers:
        handler.flush()
    content = next(tmp_path.glob('*.log')).read_text(encoding='utf-8')
    assert 'secret-value' not in content
    assert '123456' not in content
    assert 'token=abc' not in content
    assert '<redacted>' in content
```

- [ ] **Step 2: Run tests to verify RED**

```powershell
& '..\Scripts\python.exe' -m pytest testcases/test_logger.py -q
```

Expected: FAIL because `CHOPSTICKLIFE_LOG_DIR` and managed-handler redaction are not implemented.

- [ ] **Step 3: Implement managed handlers and redaction**

Replace `commons/logger.py` with:

```python
"""UTF-8 logging with managed handlers and keyed-secret redaction."""

from __future__ import annotations

import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


_log_file_path_cache: Optional[Path] = None
_SECRET_PATTERN = re.compile(
    r'(?i)\b(password|passwd|pwd|verification[_ -]?code|pay[_ -]?password|token)'
    r'(\s*[:=]\s*)([^\s,;]+)'
)


def _sanitize_log_file_tag(raw: str) -> str:
    value = re.sub(r'[^a-zA-Z0-9_-]+', '_', (raw or '').strip()).strip('_')
    return value[:48] if value else ''


def _log_file_tag_from_env_or_argv() -> str:
    configured = (os.environ.get('CHOPSTICKLIFE_LOG_FILE_TAG') or '').strip()
    if configured:
        return _sanitize_log_file_tag(configured)
    for index, argument in enumerate(sys.argv):
        if argument.lower() == '--method' and index + 1 < len(sys.argv):
            return _sanitize_log_file_tag(sys.argv[index + 1])
    return ''


def redact_text(value: object) -> str:
    return _SECRET_PATTERN.sub(
        lambda match: f'{match.group(1)}{match.group(2)}<redacted>',
        str(value),
    )


class RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact_text(record.getMessage())
        record.args = ()
        return True


def _build_log_path() -> Path:
    log_dir = Path(os.environ.get('CHOPSTICKLIFE_LOG_DIR') or 'logs')
    log_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    tag = _log_file_tag_from_env_or_argv()
    suffix = f'_{tag}' if tag else ''
    return log_dir / f'chopsticklife{suffix}_{timestamp}.log'


def setup_logger(name=None, log_level=logging.INFO) -> logging.Logger:
    global _log_file_path_cache
    if _log_file_path_cache is None:
        _log_file_path_cache = _build_log_path()

    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    logger.propagate = False
    for handler in list(logger.handlers):
        if getattr(handler, '_chopsticks_managed', False):
            logger.removeHandler(handler)
            handler.close()

    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(filename)s:%(lineno)d - %(levelname)s - %(message)s'
    )
    redactor = RedactingFilter()
    file_handler = logging.FileHandler(_log_file_path_cache, encoding='utf-8')
    console_handler = logging.StreamHandler(sys.stdout)
    for handler in (file_handler, console_handler):
        handler.setLevel(log_level)
        handler.setFormatter(formatter)
        handler.addFilter(redactor)
        handler._chopsticks_managed = True
        logger.addHandler(handler)
    return logger
```

- [ ] **Step 4: Run focused and offline tests**

```powershell
& '..\Scripts\python.exe' -m pytest testcases/test_logger.py -q
& '..\Scripts\python.exe' -m pytest -m 'not device' -q
```

Expected: all tests PASS; test output and generated log contain no test secret values.

- [ ] **Step 5: Commit**

```powershell
git add commons/logger.py testcases/test_logger.py
git commit -m "refactor: harden automation logging"
```

Expected: commit succeeds, or record `未提交：git 不可用`.

---

### Task 7: Deterministic Wait Primitives

**Files:**
- Create: `commons/waits.py`
- Create: `testcases/test_waits.py`

**Interfaces:**
- Consumes: a zero-argument predicate, monotonic clock, sleeper, Appium driver, and `(by, value)` locator tuple.
- Produces: `wait_until(predicate, *, timeout: float, interval: float = 0.1, clock=time.monotonic, sleeper=time.sleep) -> bool`, `find_optional(driver, locator, *, timeout: float, interval: float = 0.1) -> object | None`, `RequiredElementNotFound`, `find_required(driver, locator, *, timeout: float, action: str, interval: float = 0.1) -> object`.

- [ ] **Step 1: Write failing deterministic wait tests**

Create `testcases/test_waits.py`:

```python
import pytest

from commons.waits import (
    RequiredElementNotFound,
    find_optional,
    find_required,
    wait_until,
)


pytestmark = pytest.mark.unit


class FakeClock:
    def __init__(self):
        self.now = 0.0
        self.sleeps = []
    def monotonic(self):
        return self.now
    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds


class FakeDriver:
    def __init__(self, responses):
        self.responses = list(responses)
    def find_elements(self, by, value):
        if self.responses:
            return self.responses.pop(0)
        return []


def test_wait_until_returns_immediately_without_sleep():
    clock = FakeClock()
    assert wait_until(lambda: True, timeout=1, clock=clock.monotonic, sleeper=clock.sleep)
    assert clock.sleeps == []


def test_wait_until_polls_until_success():
    clock = FakeClock()
    outcomes = iter((False, False, True))
    assert wait_until(lambda: next(outcomes), timeout=1, interval=0.1, clock=clock.monotonic, sleeper=clock.sleep)
    assert clock.sleeps == [0.1, 0.1]


def test_wait_until_returns_false_at_deadline():
    clock = FakeClock()
    assert wait_until(lambda: False, timeout=0.2, interval=0.1, clock=clock.monotonic, sleeper=clock.sleep) is False
    assert clock.now == pytest.approx(0.2)


def test_find_optional_returns_none_after_timeout(monkeypatch):
    driver = FakeDriver([[], [], []])
    monkeypatch.setattr('commons.waits.time.sleep', lambda seconds: None)
    assert find_optional(driver, ('id', 'home'), timeout=0, interval=0.1) is None


def test_find_required_raises_actionable_error():
    driver = FakeDriver([[]])
    with pytest.raises(RequiredElementNotFound, match='open home'):
        find_required(driver, ('id', 'home'), timeout=0, interval=0.1, action='open home')
```

- [ ] **Step 2: Run tests to verify RED**

```powershell
& '..\Scripts\python.exe' -m pytest testcases/test_waits.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'commons.waits'`.

- [ ] **Step 3: Implement the wait primitives**

Create `commons/waits.py`:

```python
"""Deterministic condition and element waiting primitives."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import TypeVar


T = TypeVar('T')


class RequiredElementNotFound(TimeoutError):
    pass


def wait_until(
    predicate: Callable[[], T],
    *,
    timeout: float,
    interval: float = 0.1,
    clock: Callable[[], float] = time.monotonic,
    sleeper: Callable[[float], None] = time.sleep,
) -> T | bool:
    if timeout < 0:
        raise ValueError('timeout must be non-negative')
    if interval <= 0:
        raise ValueError('interval must be positive')
    deadline = clock() + timeout
    while True:
        result = predicate()
        if result:
            return result
        remaining = deadline - clock()
        if remaining <= 0:
            return False
        sleeper(min(interval, remaining))


def find_optional(driver, locator, *, timeout: float, interval: float = 0.1):
    def locate():
        elements = driver.find_elements(*locator)
        return elements[0] if elements else None
    result = wait_until(locate, timeout=timeout, interval=interval)
    return result if result is not False else None


def find_required(
    driver,
    locator,
    *,
    timeout: float,
    action: str,
    interval: float = 0.1,
):
    element = find_optional(driver, locator, timeout=timeout, interval=interval)
    if element is None:
        raise RequiredElementNotFound(
            f"Required element not found action={action!r} by={locator[0]!r} "
            f"value={locator[1]!r} timeout={timeout}"
        )
    return element
```

- [ ] **Step 4: Run focused tests**

```powershell
& '..\Scripts\python.exe' -m pytest testcases/test_waits.py -q
```

Expected: all wait tests PASS with no real-time sleep longer than test execution overhead.

- [ ] **Step 5: Commit**

```powershell
git add commons/waits.py testcases/test_waits.py
git commit -m "feat: add deterministic wait primitives"
```

Expected: commit succeeds, or record `未提交：git 不可用`.

---

### Task 8: Sanitized Failure Diagnostics

**Files:**
- Create: `commons/diagnostics.py`
- Create: `testcases/test_diagnostics.py`

**Interfaces:**
- Consumes: Appium driver attributes `current_activity`, `current_context`, `page_source`, `save_screenshot(path)` and an action string.
- Produces: immutable `FailureArtifacts(activity: str, context: str, screenshot: Path | None, page_source: Path | None)`, `sanitize_xml(text: str) -> str`, `capture_failure(driver, action: str, artifacts_dir: str | Path = 'logs') -> FailureArtifacts`.

- [ ] **Step 1: Write failing diagnostics tests**

Create `testcases/test_diagnostics.py`:

```python
import pytest

from commons.diagnostics import capture_failure


pytestmark = pytest.mark.unit


class FakeDriver:
    current_activity = '.MainActivity'
    current_context = 'NATIVE_APP'
    page_source = '<node pass' + 'word="secret" text="09123456789" content-desc="123456" />'

    def save_screenshot(self, path):
        with open(path, 'wb') as stream:
            stream.write(b'png')
        return True


class BrokenDriver:
    @property
    def current_activity(self):
        raise RuntimeError('activity unavailable')
    @property
    def current_context(self):
        raise RuntimeError('context unavailable')
    @property
    def page_source(self):
        raise RuntimeError('source unavailable')
    def save_screenshot(self, path):
        raise RuntimeError('screenshot unavailable')


def test_capture_failure_writes_sanitized_artifacts(tmp_path):
    artifacts = capture_failure(FakeDriver(), 'open / checkout', artifacts_dir=tmp_path)
    assert artifacts.activity == '.MainActivity'
    assert artifacts.context == 'NATIVE_APP'
    assert artifacts.screenshot and artifacts.screenshot.exists()
    assert artifacts.page_source and artifacts.page_source.exists()
    assert 'open_checkout' in artifacts.screenshot.name
    xml = artifacts.page_source.read_text(encoding='utf-8')
    assert 'secret' not in xml
    assert '09123456789' not in xml
    assert '123456' not in xml
    assert '<redacted>' in xml


def test_capture_failure_tolerates_unavailable_driver_evidence(tmp_path):
    artifacts = capture_failure(BrokenDriver(), 'broken', artifacts_dir=tmp_path)
    assert artifacts.activity == ''
    assert artifacts.context == ''
    assert artifacts.screenshot is None
    assert artifacts.page_source is None
```

- [ ] **Step 2: Run tests to verify RED**

```powershell
& '..\Scripts\python.exe' -m pytest testcases/test_diagnostics.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'commons.diagnostics'`.

- [ ] **Step 3: Implement sanitized diagnostics**

Create `commons/diagnostics.py`:

```python
"""Sanitized Appium failure artifacts."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from commons.logger import setup_logger


logger = setup_logger(__name__)
_ACTION_PATTERN = re.compile(r'[^a-zA-Z0-9_-]+')
_KEYED_ATTRIBUTE = re.compile(
    r"(?i)((?:password|passwd|pwd|verification[_ -]?code|pay[_ -]?password|token)\s*=\s*[\"'])(.*?)([\"'])"
)
_PHONE_LIKE = re.compile(r'(?<!\d)(?:\d[ -]?){6,14}\d(?!\d)')
_SHORT_CODE_ATTRIBUTE = re.compile(r"((?:text|content-desc)\s*=\s*[\"'])\d{4,8}([\"'])")


@dataclass(frozen=True)
class FailureArtifacts:
    activity: str
    context: str
    screenshot: Path | None
    page_source: Path | None


def _safe_driver_value(driver, attribute: str) -> str:
    try:
        return str(getattr(driver, attribute) or '')
    except Exception:
        return ''


def _safe_action(action: str) -> str:
    value = _ACTION_PATTERN.sub('_', (action or '').strip()).strip('_')
    return value[:48] or 'failure'


def sanitize_xml(text: str) -> str:
    sanitized = _KEYED_ATTRIBUTE.sub(r'\1<redacted>\3', text or '')
    sanitized = _PHONE_LIKE.sub('<redacted>', sanitized)
    return _SHORT_CODE_ATTRIBUTE.sub(r'\1<redacted>\2', sanitized)


def capture_failure(driver, action: str, artifacts_dir: str | Path = 'logs') -> FailureArtifacts:
    root = Path(artifacts_dir)
    root.mkdir(parents=True, exist_ok=True)
    prefix = f"{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}_{_safe_action(action)}"
    screenshot_path = root / f'{prefix}.png'
    source_path = root / f'{prefix}.xml'
    saved_screenshot = None
    saved_source = None

    try:
        if driver.save_screenshot(str(screenshot_path)):
            saved_screenshot = screenshot_path
    except Exception as exc:
        logger.warning(
            'failure screenshot unavailable action=%s error_type=%s',
            _safe_action(action),
            type(exc).__name__,
        )

    try:
        source_path.write_text(sanitize_xml(driver.page_source), encoding='utf-8')
        saved_source = source_path
    except Exception as exc:
        logger.warning(
            'failure page source unavailable action=%s error_type=%s',
            _safe_action(action),
            type(exc).__name__,
        )

    return FailureArtifacts(
        activity=_safe_driver_value(driver, 'current_activity'),
        context=_safe_driver_value(driver, 'current_context'),
        screenshot=saved_screenshot,
        page_source=saved_source,
    )
```

- [ ] **Step 4: Run diagnostics and offline regression tests**

```powershell
& '..\Scripts\python.exe' -m pytest testcases/test_diagnostics.py testcases/test_logger.py -q
& '..\Scripts\python.exe' -m pytest -m 'not device' -q
```

Expected: diagnostics tests PASS, all offline tests pass, and test artifact text contains no supplied secret or phone values.

- [ ] **Step 5: Commit**

```powershell
git add commons/diagnostics.py testcases/test_diagnostics.py
git commit -m "feat: capture sanitized failure diagnostics"
```

Expected: commit succeeds, or record `未提交：git 不可用`.

---

### Task 9: Foundation Verification and Review Report

**Files:**
- Verify: `commons/config.py`
- Verify: `commons/android_runtime.py`
- Verify: `commons/driver.py`
- Verify: `commons/logger.py`
- Verify: `commons/waits.py`
- Verify: `commons/diagnostics.py`
- Verify: `pages/app_common.py`
- Verify: `testcases/`
- Create: `docs/reviews/2026-07-22-foundation-review.md`

**Interfaces:**
- Consumes: Tasks 1-8 and the approved design spec.
- Produces: fresh offline verification output, before/after risk counts, cleanup recovery reference, and explicit blockers for the next domain plan.

- [ ] **Step 1: Run syntax compilation without retaining bytecode**

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
& '..\Scripts\python.exe' -m compileall -q -f commons pages flows scripts testcases
Remove-Item Env:PYTHONDONTWRITEBYTECODE
```

Expected: exit code `0`, no syntax errors.

- [ ] **Step 2: Run the complete offline suite**

```powershell
& '..\Scripts\python.exe' -m pytest -m 'not device' -q
```

Expected: zero failed tests. Device-marked tests are reported as deselected, not silently skipped by changed assertions.

- [ ] **Step 3: Run dependency and Appium health checks**

```powershell
& '..\Scripts\python.exe' -m pip check
Invoke-RestMethod -Uri 'http://127.0.0.1:4723/status' -TimeoutSec 3 | ConvertTo-Json -Depth 8
```

Expected: `No broken requirements found`; Appium response has `value.ready: true`.

- [ ] **Step 4: Collect residual-risk counts**

```powershell
$sleepCount = (rg -n --glob '*.py' 'time\.sleep' commons pages flows scripts testcases | Measure-Object).Count
$broadExceptCount = (rg -n --glob '*.py' 'except Exception|except:' commons pages flows scripts testcases | Measure-Object).Count
$largeFiles = Get-ChildItem commons,pages,flows,scripts,testcases -Recurse -File -Filter '*.py' |
  ForEach-Object { [PSCustomObject]@{Path=$_.FullName.Substring($pwd.Path.Length+1); Lines=(Get-Content -LiteralPath $_.FullName).Count} } |
  Where-Object Lines -gt 800 |
  Sort-Object Lines -Descending
[PSCustomObject]@{FixedSleeps=$sleepCount; BroadExceptions=$broadExceptCount}
$largeFiles
```

Expected: command succeeds. This foundation plan does not require domain-level counts to reach zero; the exact residual list becomes input to later domain plans.

- [ ] **Step 5: Scan for committed secrets**

```powershell
$matches = rg -n --hidden --glob '!.git/**' --glob '!*.log' --glob '!*.png' '(?i)(password|passwd|pwd|verification[_ -]?code|pay[_ -]?password|token)\s*[:=]\s*["''][^"'']+["'']' .
if ($LASTEXITCODE -eq 0) { $matches; throw 'Potential hard-coded secret found' }
if ($LASTEXITCODE -ne 1) { throw "rg failed with exit code $LASTEXITCODE" }
```

Expected: exit code `0` for the PowerShell block and no potential hard-coded secret output. Test-only sentinel strings must be constructed locally or explicitly documented if the scanner flags them.

- [ ] **Step 6: Write the review report**

Create `docs/reviews/2026-07-22-foundation-review.md` containing these concrete sections populated from fresh command output:

```markdown
# 公共基础层审查与重构报告

## 清理与恢复

- 备份文件路径、SHA-256、清单条目数
- 已删除路径
- 明确恢复命令

## 离线验证

- Python 版本
- pytest 通过、失败、跳过、取消选择数量
- `pip check` 结果

## 已治理风险

- 配置来源与优先级
- Android 启动策略
- Driver 生命周期
- 日志编码与脱敏
- 等待与诊断公共接口

## 遗留风险

- 固定等待数量及主要文件
- 宽泛异常数量及主要文件
- 超过 800 行的文件
- 未执行的真机验证及原因

## 下一阶段入口条件

- 离线测试必须保持零失败
- 从登录与首页计划开始接入公共等待和诊断接口
```

- [ ] **Step 7: Final commit**

```powershell
git add commons pages/app_common.py testcases pytest.ini docs/reviews/2026-07-22-foundation-review.md docs/superpowers
git commit -m "test: verify automation foundation refactor"
```

Expected: commit succeeds. If Git remains unavailable, the report must state `未提交：git 不可用` and list all modified files.

---

## Plan Self-Review Checklist

- Every cleanup target is copied and hash-verified before deletion.
- `pyvenv.cfg` and `logs/shipping_new_user_guide.png` are explicitly preserved.
- All new production functions are introduced by failing tests.
- Compatibility imports and method names used by current scripts remain available.
- No task runs a real device flow, order creation, payment, verification-code send, or data mutation.
- All verification commands have explicit expected evidence.
- Later business-domain refactors remain out of this plan and will receive separate plans after this foundation passes.
