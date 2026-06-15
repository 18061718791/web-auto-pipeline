"""
AssertHealer — 断言自愈（DB 字段类型自动检测）

核心问题：写 DB 断言时猜错字段类型（如 boolean 当成 integer 比较），
导致断言永远静默失败。

自愈方案：
  1. 自动查 information_schema.columns 确认数据类型
  2. 根据类型选择正确的比较方式
  3. 缓存查询结果，避免重复查库

用法：
    from core.healer.assert_healer import AssertHealer
    healer = AssertHealer(get_db_connection)
    healer.assert_db_value(
        report, "DB: 已软删除",
        "device_tags", "is_delete",
        row[0], True,
    )
"""

from typing import Callable, Optional, Any

from core.healer._base import HealerBase


class AssertHealer(HealerBase):
    """DB 断言自愈 — 自动匹配字段类型"""

    # Python 类型 → 数据类型的映射
    TYPE_MAP = {
        "boolean": "bool",
        "bool": "bool",
        "integer": "int",
        "smallint": "int",
        "bigint": "int",
        "numeric": "float",
        "double precision": "float",
        "real": "float",
        "character varying": "str",
        "character": "str",
        "text": "str",
        "varchar": "str",
        "timestamp": "datetime",
        "date": "date",
        "json": "json",
        "jsonb": "json",
    }

    def __init__(self, db_connection_fn: Callable):
        """
        Args:
            db_connection_fn: 返回数据库连接的函数
        """
        self._db_fn = db_connection_fn
        self._type_cache = {}
        self._stats = {"hits": 0, "misses": 0}

    def get_column_type(self, table: str, column: str) -> Optional[str]:
        """获取字段数据类型（缓存式）"""
        key = f"{table}.{column}"
        if key not in self._type_cache:
            try:
                conn = self._db_fn()
                cur = conn.cursor()
                cur.execute(
                    """
                    SELECT data_type
                    FROM information_schema.columns
                    WHERE table_name = %s AND column_name = %s
                """,
                    (table, column),
                )
                row = cur.fetchone()
                cur.close()
                conn.close()
                if row:
                    raw_type = row[0].lower()
                    mapped = self.TYPE_MAP.get(raw_type, raw_type)
                    self._type_cache[key] = mapped
                else:
                    self._type_cache[key] = "unknown"
                    self._log(f"⚠️ 列 {key} 在 information_schema 中未找到")
            except Exception as e:
                self._type_cache[key] = "error"
                self._log(f"❌ 查询列类型失败: {e}")

        return self._type_cache[key]

    def assert_db_value(
        self,
        report,
        desc: str,
        table: str,
        column: str,
        actual_value: Any,
        expected: Any,
    ) -> bool:
        """自动适配类型的 DB 断言

        Args:
            report: TestReport 实例
            desc: 断言描述
            table: 表名
            column: 列名
            actual_value: 实际从 DB 读取的值
            expected: 期望值

        Returns:
            断言是否通过
        """
        col_type = self.get_column_type(table, column)
        self._stats["hits"] += 1

        # 根据字段类型选择比较方式
        if col_type == "bool" or col_type == "boolean":
            # boolean 类型：用 is True / is False
            if isinstance(expected, bool):
                result = actual_value is expected
            else:
                result = actual_value is True if expected else actual_value is False

        elif col_type in ("int", "integer", "smallint", "bigint"):
            try:
                result = actual_value == int(expected)
            except (ValueError, TypeError):
                result = False

        elif col_type in ("str", "text", "varchar"):
            try:
                result = actual_value == str(expected)
            except Exception:
                result = False

        elif col_type == "float":
            try:
                result = abs(float(actual_value) - float(expected)) < 0.0001
            except (ValueError, TypeError):
                result = False

        elif col_type == "json":
            import json

            try:
                result = json.dumps(actual_value, sort_keys=True) == json.dumps(
                    expected, sort_keys=True
                )
            except Exception:
                result = str(actual_value) == str(expected)

        else:
            # 未知类型：用字符串比较
            result = str(actual_value) == str(expected)

        # 记录到报告
        detail = f"type={col_type}, actual={actual_value}, expected={expected}"
        report.assertion(desc, result, detail)

        if not result:
            self._log(
                f"❌ 断言失败: {desc} [{col_type}] 期望={expected}, 实际={actual_value}"
            )
        return result

    def probe_table(self, table: str) -> list[dict]:
        """探测表结构 — 打印所有列名和类型"""
        rows = []
        try:
            conn = self._db_fn()
            cur = conn.cursor()
            cur.execute(
                """
                SELECT column_name, data_type, is_nullable,
                       column_default
                FROM information_schema.columns
                WHERE table_name = %s
                ORDER BY ordinal_position
            """,
                (table,),
            )
            for col in cur.fetchall():
                rows.append(
                    {
                        "column": col[0],
                        "type": col[1],
                        "nullable": col[2],
                        "default": col[3],
                    }
                )
            cur.close()
            conn.close()
        except Exception as e:
            self._log(f"❌ 探测表结构失败: {e}")
        return rows

    def probe_and_print(self, table: str):
        """打印表结构（调试用）"""
        cols = self.probe_table(table)
        print(f"\n  [AssertHealer] 表结构: {table}")
        print(f"  {'列名':25s} {'类型':15s} {'可空':6s} {'默认值'}")
        print(f"  {'-' * 55}")
        for col in cols:
            print(
                f"  {col['column']:25s} {col['type']:15s} "
                f"{col['nullable']:6s} {col['default'] or '-':s}"
            )
        print()

    def stats(self) -> dict:
        return dict(self._stats)
