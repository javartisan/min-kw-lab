#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
学习小点：Neo4j + Cypher（真实 Bolt 连接）
一句话：属性图引擎；App 经 Bolt 连接，用参数化 Cypher 读写。

对应笔记：docs/3-知识存储.html → Neo4j
工程实践：
  - neo4j 官方 Driver + 会话/事务
  - MERGE 幂等入库；MATCH 参数绑定
  - 学习数据用 lab 属性隔离

依赖：本地 Neo4j 已手动启动；.env 配置正确；pip install -r requirements.txt
首次建议：python -m common.seed_kg
"""

from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from common.bootstrap import ensure_src_on_path
from common.neo4j_client import get_lab_tag, require_neo4j, run_cypher
from common.seed_kg import ensure_seed_graph

ensure_src_on_path()


def demo_merge_and_match() -> None:
    lab = get_lab_tag()

    print("\n【1] MERGE 公司（第二次应复用，不重复建点）")
    for i in range(2):
        rows = run_cypher(
            """
            MERGE (c:Company {name: $name, lab: $lab})
            ON CREATE SET c.createdAt = datetime(), c.entityType = 'Company',
                          c._demo = true
            ON MATCH  SET c.touchedAt = datetime()
            RETURN c.name AS name,
                   c.createdAt IS NOT NULL AS has_created,
                   c.touchedAt IS NOT NULL AS has_touched
            """,
            {"name": "演示公司-学习用", "lab": lab},
            write=True,
        )
        print(f"  round={i+1}  {rows[0]}")

    print("\n【2] MERGE 行业边 BELONGS_TO")
    run_cypher(
        """
        MERGE (i:Industry {name: $ind, lab: $lab})
        ON CREATE SET i.entityType = 'Industry'
        WITH i
        MATCH (c:Company {name: $name, lab: $lab})
        MERGE (c)-[r:BELONGS_TO {lab: $lab}]->(i)
        RETURN c.name AS company, type(r) AS rel, i.name AS industry
        """,
        {"name": "演示公司-学习用", "ind": "演示行业", "lab": lab},
        write=True,
    )
    print("  OK")

    print("\n【3] 参数化查询 name CONTAINS $keyword")
    rows = run_cypher(
        """
        MATCH (n {lab: $lab})-[r]->(m {lab: $lab})
        WHERE n.name CONTAINS $keyword
        RETURN n.name AS from, type(r) AS rel, m.name AS to
        LIMIT 20
        """,
        {"lab": lab, "keyword": "茅台"},
    )
    for row in rows:
        print(f"  ({row['from']})-[{row['rel']}]->({row['to']})")

    print("\n【4] 多跳 CONTROLS*1..3")
    rows = run_cypher(
        """
        MATCH path = (a:Company {lab: $lab})-[:CONTROLS*1..3]->(b:Company {lab: $lab})
        WHERE a.name = $name
        RETURN [n IN nodes(path) | n.name] AS names
        LIMIT 10
        """,
        {"lab": lab, "name": "茅台集团"},
    )
    for row in rows:
        print("  " + " → ".join(row["names"]))


def demo() -> None:
    print("=" * 60)
    print("Neo4j/Cypher：真实 Driver + MERGE / MATCH")
    print("=" * 60)

    with require_neo4j():
        stats = ensure_seed_graph(reset=False)
        print(f"\n【种子图谱】lab={stats['lab']} nodes={stats['nodes']} rels={stats['rels']}")
        demo_merge_and_match()
        print("\n安全要点：名称用 $参数绑定；学习节点一律带 lab，清数据只 DETACH DELETE lab 子图。")


if __name__ == "__main__":
    demo()
