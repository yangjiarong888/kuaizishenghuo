"""登录自动化：与 App UI 相关的常量（包名、定位器元组、树特征）。"""

from typing import Tuple

from appium.webdriver.common.appiumby import AppiumBy

from pages.login.data import Locator

# page_source 中「验证码登录主 CTA」常见字面
SMS_PAGE_SOURCE_SEND_MARKERS: Tuple[str, ...] = (
    'content-desc="获取短信验证码"',
    "获取短信验证码",
    'content-desc="发送验证码"',
    "发送验证码",
    'content-desc="获取验证码"',
    "获取验证码",
    "发送短信验证码",
    "免费获取",
    "免费获取验证码",
    "重获验证",
    "重获验证码",
)

HOME_H5_TRAP_RES_ID_MARKERS: Tuple[str, ...] = (
    "banner_middle",
    "ll_exchange_rate",
)

QQ_CLIENT_PACKAGES: Tuple[str, ...] = (
    "com.tencent.mobileqq",
    "com.tencent.tim",
    "com.tencent.qqlite",
)

QQ_OAUTH_BROWSER_PACKAGES: Tuple[str, ...] = (
    "com.android.chrome",
    "com.chrome.beta",
    "com.microsoft.emmx",
    "org.mozilla.firefox",
    "com.sec.android.app.sbrowser",
    "com.huawei.browser",
)

LOGIN_HUB_LOCS: Tuple[Locator, ...] = (
    (AppiumBy.XPATH, '//*[contains(@text,"登录或注册")]'),
    (AppiumBy.XPATH, '//*[@content-desc="登录或注册"]'),
    (AppiumBy.XPATH, '//*[contains(@text,"微信账号快捷登录")]'),
    (AppiumBy.XPATH, '//*[@content-desc="微信账号快捷登录"]'),
    (AppiumBy.XPATH, '//*[contains(@text,"QQ账号快捷登录")]'),
    (AppiumBy.XPATH, '//*[@content-desc="QQ账号快捷登录"]'),
    (AppiumBy.XPATH, '//*[contains(@text,"谷歌账号快捷登录")]'),
    (AppiumBy.XPATH, '//*[@content-desc="谷歌账号快捷登录"]'),
    (AppiumBy.XPATH, '//*[contains(@text,"手机号码登录/注册")]'),
    (AppiumBy.XPATH, '//*[@content-desc="手机号码登录/注册"]'),
    (AppiumBy.XPATH, '//*[contains(@text,"手机号码登录")]'),
)
