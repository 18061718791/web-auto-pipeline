"""
Platform-aware config router.
用法: from config import BASE_URL, get_db_connection
自动解析到当前活动的平台配置。
"""
import os, importlib, sys

_PLATFORM = os.environ.get('PLATFORM', 'iot')

_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

_mod = importlib.import_module(f'platforms.{_PLATFORM}.config')
for _attr in dir(_mod):
    if not _attr.startswith('_'):
        globals()[_attr] = getattr(_mod, _attr)
