# -*- coding: utf-8 -*-
"""
Neo4j 工程连接层（学习脚本共用）

实务习惯：
  - URI / 账号来自环境变量或项目根 .env（勿把密码写进代码）
  - 参数化 Cypher（$name），禁止字符串拼接用户输入
  - Driver 单例 + 用完 close；短脚本也可用 with get_driver() as driver
  - 学习数据用 lab 属性隔离，避免误删你库里其它业务图
"""

from __future__ import annotations

import os
import sys
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterator, Optional

# 项目根：.../min-kw-lab
_ROOT = Path(__file__).resolve().parents[2]


def _load_dotenv() -> None:
    env_path = _ROOT / ".env"
    if not env_path.exists():
        return
    try:
        from dotenv import load_dotenv

        load_dotenv(env_path)
    except ImportError:
        # 无 python-dotenv 时手写解析，保证可跑
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_dotenv()


def get_lab_tag() -> str:
    return os.getenv("NEO4J_LAB_TAG", "min-kw-lab")


def _settings() -> dict[str, str]:
    return {
        "uri": os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        "user": os.getenv("NEO4J_USER", "neo4j"),
        "password": os.getenv("NEO4J_PASSWORD", "password"),
    }


@lru_cache(maxsize=1)
def get_driver():
    """
    返回 neo4j.Driver（懒加载单例）。
    调用方应在脚本结束时 driver.close()，或使用 require_neo4j() 上下文。
    """
    try:
        from neo4j import GraphDatabase
    except ImportError as e:
        raise SystemExit(
            "缺少 neo4j 驱动。请先：\n"
            "  source venv/bin/activate && pip install -r requirements.txt"
        ) from e

    cfg = _settings()
    driver = GraphDatabase.driver(cfg["uri"], auth=(cfg["user"], cfg["password"]))
    return driver


def run_cypher(
    query: str,
    parameters: Optional[dict[str, Any]] = None,
    *,
    write: bool = False,
) -> list[dict[str, Any]]:
    """
    执行一条 Cypher，返回 list[dict]（每行一个记录）。
    write=True 走写事务（MERGE/DELETE）；默认只读。
    """
    driver = get_driver()
    params = parameters or {}

    def _work(tx):
        result = tx.run(query, params)
        return [r.data() for r in result]

    with driver.session() as session:
        if write:
            return session.execute_write(_work)
        return session.execute_read(_work)


@contextmanager
def require_neo4j() -> Iterator[Any]:
    """
    with require_neo4j() as driver:
        ...
    连不上时打印清晰指引后退出（不启动数据库，由你手动开）。
    """
    cfg = _settings()
    driver = get_driver()
    try:
        driver.verify_connectivity()
    except Exception as e:
        print("=" * 60, file=sys.stderr)
        print("无法连接 Neo4j，请先手动启动图数据库后再跑本脚本。", file=sys.stderr)
        print(f"  URI : {cfg['uri']}", file=sys.stderr)
        print(f"  USER: {cfg['user']}", file=sys.stderr)
        print("  可选：docker compose up -d   # 本仓库 docker-compose.yml", file=sys.stderr)
        print("  或启动你本机已有的 Neo4j，并核对 .env 中密码。", file=sys.stderr)
        print(f"  原因: {e}", file=sys.stderr)
        print("=" * 60, file=sys.stderr)
        try:
            driver.close()
        except Exception:
            pass
        get_driver.cache_clear()
        raise SystemExit(1) from e

    try:
        yield driver
    finally:
        driver.close()
        get_driver.cache_clear()
