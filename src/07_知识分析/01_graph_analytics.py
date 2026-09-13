#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
学习小点：图分析（Neo4j Cypher）
一句话：中心性、路径、社区粗分 —— 挖「谁重要、谁一伙、怎么连」。

对应笔记：docs/7-知识分析.html → 图分析
入门用 Cypher 聚合/路径；进阶可上 Neo4j GDS（PageRank / Louvain）。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from common.neo4j_client import get_lab_tag, require_neo4j, run_cypher
from common.seed_kg import ensure_seed_graph


def demo() -> None:
    print("=" * 60)
    print("图分析：度中心性 / 最短路径 / 共同邻居（Neo4j）")
    print("=" * 60)

    with require_neo4j():
        ensure_seed_graph(reset=False)
        lab = get_lab_tag()

        print("\n【度中心性 Top】（无向邻接计数）")
        rows = run_cypher(
            """
            MATCH (c:Company {lab: $lab})-[r]-(n {lab: $lab})
            RETURN c.name AS company, count(r) AS degree
            ORDER BY degree DESC
            LIMIT 10
            """,
            {"lab": lab},
        )
        for row in rows:
            print(f"  {row['company']:8s}  degree={row['degree']}")

        print("\n【最短路径】茅台集团 → 五粮液")
        rows = run_cypher(
            """
            MATCH (a:Company {name: $a, lab: $lab}),
                  (b:Company {name: $b, lab: $lab})
            MATCH path = shortestPath((a)-[*..6]-(b))
            RETURN [n IN nodes(path) | n.name] AS names,
                   [r IN relationships(path) | type(r)] AS rels
            """,
            {"a": "茅台集团", "b": "五粮液", "lab": lab},
        )
        if not rows:
            print("  不可达")
        for row in rows:
            print("  节点: " + " → ".join(row["names"]))
            print("  边型: " + " / ".join(row["rels"]))

        print("\n【共同邻居相似】贵州茅台 vs 五粮液 / 宁德时代")
        for other in ("五粮液", "宁德时代"):
            rows = run_cypher(
                """
                MATCH (a:Company {name: $a, lab: $lab})--(n {lab: $lab})
                WITH a, collect(DISTINCT n.name) AS na
                MATCH (b:Company {name: $b, lab: $lab})--(m {lab: $lab})
                WITH na, collect(DISTINCT m.name) AS nb
                WITH [x IN na WHERE x IN nb] AS inter, na, nb
                RETURN size(inter) * 1.0 /
                       CASE WHEN size(na) + size(nb) - size(inter) = 0 THEN 1
                            ELSE size(na) + size(nb) - size(inter) END AS jaccard
                """,
                {"a": "贵州茅台", "b": other, "lab": lab},
            )
            print(f"  vs {other}: jaccard={rows[0]['jaccard']:.2f}")

        print("\n【连通分量粗社区】（弱连通：无向展开）")
        # 简化：按 Industry 抱团 + 无行业公司单独列出
        rows = run_cypher(
            """
            MATCH (c:Company {lab: $lab})-[:BELONGS_TO]->(i:Industry {lab: $lab})
            RETURN i.name AS community, collect(c.name) AS members
            ORDER BY community
            """,
            {"lab": lab},
        )
        for row in rows:
            print(f"  {row['community']}: {row['members']}")

    print("\n进阶：把 pagerank / communityId 写回节点属性，供问答过滤。")


if __name__ == "__main__":
    demo()
