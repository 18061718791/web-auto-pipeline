#!/usr/bin/env python3
"""Web 平台自动化 — 统一入口

用法:
  python run.py                     # IoT 有头模式
  python run.py --headless          # IoT 无头模式
  python run.py --platform tckz     # TCKZ 平台
  python run.py --list-scripts      # 列出可用脚本
"""
import sys, os, argparse

_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

def main():
    parser = argparse.ArgumentParser(description='Web 平台自动化测试统一入口')
    parser.add_argument('--platform', '-p', default='iot',
                        help='平台标识 (iot, tckz, 等)')
    parser.add_argument('--headless', action='store_true',
                        help='无头模式执行')
    parser.add_argument('--list-scripts', action='store_true',
                        help='列出平台可用脚本')
    parser.add_argument('--only', type=str, default='',
                        help='仅执行指定脚本，逗号分隔')
    parser.add_argument('--exclude', type=str, default='',
                        help='排除指定脚本，逗号分隔')
    args = parser.parse_args()

    os.environ['PLATFORM'] = args.platform

    if args.list_scripts:
        from core.runner import list_scripts
        list_scripts()
    else:
        from core.runner import main as run_main
        run_main()

if __name__ == '__main__':
    main()
