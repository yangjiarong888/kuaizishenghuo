"""page_source、OAuth 树语义、验证码解析与混合页诊断日志。"""
from __future__ import annotations

import os
import re
from typing import Optional, Tuple

from commons.logger import setup_logger

logger = setup_logger("pages.login")

class LoginSemanticsMixin:
    def _page_hints_qq_oauth_layer(self) -> bool:
        """宿主 App 内嵌 H5/半屏授权时 package 不变，用文案与常见 OAuth 域名判断。"""
        s = self._get_page_source()
        if len(s) < 80:
            return False
        url_marks = (
            "graph.qq.com",
            "open.qq.com",
            "connect.qq.com",
            "cgi-bin/oauth",
        )
        if any(m in s for m in url_marks):
            return True
        text_marks = (
            "QQ授权登录",
            "使用QQ账号",
            "应用授权",
            "选择QQ账号",
            "简版授权页",
            "Tencent",
            "redirect_uri",
            "client_id",
            "unionid",
            "access_token",
        )
        if any(m in s for m in text_marks):
            return True
        return "oauth" in s.lower() and ("qq" in s.lower() or "tencent" in s.lower())

    def _page_hints_wechat_oauth_layer(self) -> bool:
        """微信 OAuth 在应用内 WebView 时 package 仍为宿主，用语义与常见域名判断。"""
        s = self._get_page_source()
        if len(s) < 80:
            return False
        url_marks = (
            "open.weixin.qq.com",
            "wxoauth",
            "weixin.qq.com",
        )
        if any(m in s.lower() for m in url_marks):
            return True
        text_marks = (
            "微信授权",
            "使用微信登录",
            "微信登录",
            "获取你的微信头像",
            "获取你的昵称",
            "使用微信账号",
        )
        return any(m in s for m in text_marks)

    def _get_page_source(self) -> str:
        try:
            return self.driver.page_source or ""
        except Exception:
            return ""

    def log_current_screen_hybrid_diagnostics(self, reason: str) -> None:
        """
        失败时把当前包名、Activity、contexts、树里的 WebView/关键词片段写入日志，便于对照 Inspector。

        其中「充值缴费」「头条」「汇率换算」等是**首页/子页识别用文案**，来自 App 控件树，不是对业务的测试断言。
        不需要长日志时设环境变量：LOGIN_SCREEN_DIAGNOSTIC=0（或 off/false/no）。
        """
        diag = (os.environ.get("LOGIN_SCREEN_DIAGNOSTIC") or "1").strip().lower()
        if diag in ("0", "false", "no", "n", "off", "skip", "none"):
            logger.debug("[诊断·混合页] 已跳过 LOGIN_SCREEN_DIAGNOSTIC=%s | %s", diag, reason)
            return
        pkg = act = ""
        try:
            pkg = getattr(self.driver, "current_package", "") or ""
        except Exception:
            pass
        try:
            act = getattr(self.driver, "current_activity", "") or ""
        except Exception:
            pass
        contexts: Tuple[str, ...] = ()
        try:
            contexts = tuple(self.driver.contexts or ())
        except Exception:
            pass
        src = self._get_page_source()
        webview_nodes = src.count("android.webkit.WebView")
        has_recharge = "充值缴费" in src
        has_headline_tab = "头条" in src and "tv_title" in src
        has_back_white = "iv_back_white" in src
        url_like = bool(re.search(r"https?://", src[:80000]))  # 控件树里偶现 url 属性
        # 与登录后常见「子页」对照，便于判断是不是汇率工具页 / 运营活动 H5
        has_rate_page = "汇率换算" in src
        activity_hints = (
            "新店特惠",
            "新店专享",
            "领券",
            "活动",
            "限时",
            "广告",
            "跳过",
            "不感兴趣",
        )
        matched_activity = [k for k in activity_hints if k in src]

        logger.warning(
            "[诊断·混合页] %s | package=%s activity=%s | contexts=%s | "
            "WebView节点数=%s | 树中含「充值缴费」=%s 含头条标题区=%s | iv_back_white=%s | 树中含http(s)片段=%s | "
            "疑似汇率页=%s | 树中命中活动/运营类关键词=%s",
            reason,
            pkg or "?",
            act or "?",
            list(contexts) if contexts else "?",
            webview_nodes,
            has_recharge,
            has_headline_tab,
            has_back_white,
            url_like,
            has_rate_page,
            matched_activity or "无",
        )
        if webview_nodes > 0:
            logger.warning(
                "[诊断·混合页] 说明：活动/运营落地常见两类——① 纯原生 Activity（树里无 WebView，"
                "靠 Activity 名如 FestivalsDetail）；② 原生壳 + WebView（H5，树里可见 android.webkit.WebView）。"
                "二者都可能挡住首页金刚区；可系统 back 或点 iv_back / iv_back_white，再切底部「首页」Tab。"
            )

    def _extract_verification_code_from_page(self) -> Optional[str]:
        """
        从 page_source 用正则抽数字串；XML 里 bounds/id 等也含多位数字，**极易误判**。
        默认不在 _require_code 中调用；仅当环境变量 LOGIN_SMS_PARSE_CODE_FROM_PAGE=1 时启用。
        """
        src = self._get_page_source()
        # 找 4-8 位数字里更像验证码的（优先 6 位）
        candidates = re.findall(r"\b(\d{6})\b", src)
        if candidates:
            return candidates[-1]
        # 兜底：4-8 位数字
        candidates2 = re.findall(r"\b(\d{4,8})\b", src)
        if candidates2:
            return candidates2[-1]
        return None

    def _require_code(self) -> str:
        if self.data.verification_code:
            return self.data.verification_code
        allow_parse = (os.environ.get("LOGIN_SMS_PARSE_CODE_FROM_PAGE") or "").strip().lower() in (
            "1",
            "true",
            "yes",
            "y",
            "on",
        )
        if allow_parse:
            code = self._extract_verification_code_from_page()
            if code:
                logger.warning(
                    "已用 page_source 正则得到 %s 位数字作为验证码（LOGIN_SMS_PARSE_CODE_FROM_PAGE=1，易误判）",
                    len(code),
                )
                return code
        return input("请输入短信验证码（终端手动输入后回车）：").strip()
