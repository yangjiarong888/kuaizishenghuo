"""登录后行为相关环境变量开关。"""

import os


def _post_login_subpage_escape_enabled() -> bool:
    v = os.environ.get("POST_LOGIN_SUBPAGE_ESCAPE", "off").strip().lower()
    return v in ("1", "true", "yes", "y", "on", "full", "enabled")


def _post_login_headline_h5_escape_enabled() -> bool:
    v = os.environ.get("POST_LOGIN_HEADLINE_ESCAPE", "on").strip().lower()
    return v not in ("0", "false", "no", "off", "skip", "none", "disabled")
