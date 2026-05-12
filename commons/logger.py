# commons/logger.py
"""
日志配置模块
"""
import logging
import os
import re
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

# 同一次进程内共用一个文件路径，避免 driver / login_page / __main__ 各建一个时间戳文件
_log_file_path_cache: Optional[Path] = None


def _sanitize_log_file_tag(raw: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9_-]+", "_", (raw or "").strip()).strip("_")
    return s[:48] if s else ""


def _log_file_tag_from_env_or_argv() -> str:
    env = (os.environ.get("CHOPSTICKLIFE_LOG_FILE_TAG") or "").strip()
    if env:
        return _sanitize_log_file_tag(env)
    for i, arg in enumerate(sys.argv):
        if arg == "--method" or arg.lower() == "--method":
            if i + 1 < len(sys.argv):
                return _sanitize_log_file_tag(sys.argv[i + 1])
            break
    return ""


def setup_logger(name=None, log_level=logging.INFO):
    """
    设置日志配置
    
    Args:
        name: 日志器名称
        log_level: 日志级别
    
    Returns:
        logging.Logger: 配置好的日志器
    
    日志文件：
    - 命令行含 `--method wechat`（或已设环境变量 CHOPSTICKLIFE_LOG_FILE_TAG）时：
      logs/chopsticklife_wechat_YYYYMMDD_HHMMSS.log
    - 否则：logs/chopsticklife_YYYYMMDD_HHMMSS.log
    """
    global _log_file_path_cache
    # 创建日志目录
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    if _log_file_path_cache is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        tag = _log_file_tag_from_env_or_argv()
        if tag:
            _log_file_path_cache = log_dir / f"chopsticklife_{tag}_{timestamp}.log"
        else:
            _log_file_path_cache = log_dir / f"chopsticklife_{timestamp}.log"
    log_filename = _log_file_path_cache
    
    # 创建日志器
    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    
    # 清除已有的处理器（避免重复）
    logger.handlers.clear()
    
    # 创建文件处理器
    file_handler = logging.FileHandler(log_filename, encoding='utf-8')
    file_handler.setLevel(log_level)
    
    # Windows 控制台默认 GBK，emoji/部分中文会触发 UnicodeEncodeError
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    # 创建控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    
    # 创建格式化器（filename/lineno 为发出日志的 .py 文件与行号）
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(filename)s:%(lineno)d - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # 添加处理器到日志器
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger