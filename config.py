"""
Platform-aware config router.
用法: from config import BASE_URL, get_db_connection
自动解析到当前活动的平台配置。

支持通过环境变量 PLATFORMS_DIR 自定义 platforms 根目录：
  set PLATFORMS_DIR=D:\\path\\to\\platforms
  python run.py
"""

import os, importlib, sys

_PLATFORM = os.environ.get("PLATFORM", "iot")
_PLATFORMS_DIR = os.environ.get("PLATFORMS_DIR", "")

if _PLATFORMS_DIR:
    if _PLATFORMS_DIR not in sys.path:
        sys.path.insert(0, _PLATFORMS_DIR)
    _mod_path = f"{_PLATFORM}.config"
else:
    _PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
    if _PROJECT_ROOT not in sys.path:
        sys.path.insert(0, _PROJECT_ROOT)
    _mod_path = f"platforms.{_PLATFORM}.config"

_mod = importlib.import_module(_mod_path)
for _attr in dir(_mod):
    if not _attr.startswith("_"):
        globals()[_attr] = getattr(_mod, _attr)
