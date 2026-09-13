#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
学习小点：指标洞察（Neo4j 聚合 = 迷你 getStats）
一句话：把业务问题定义成可计算指标，在图谱上聚合与监控。

对应笔记：docs/7-知识分析.html → 指标洞察
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from common.neo4j_client import get_lab_tag, require_neo4j, run_cypher
from common.seed_kg import ensure_seed_graph


def demo() -> None:
    print("=" * 60)
    print("指标洞察：规模 / 分布 / 质量（Neo4j）")
    print("=" * 60)

    with require_neo4j():
        ensure_seed_graph(reset=False)
        lab = get_lab_tag()

        print("\n【总览 getStats】")
        overview = run_cypher(
            """
            MATCH (n {lab: $lab})
            WITH count(n) AS entities
            MATCH ()-[r {lab: $lab}]->()
            RETURN entities, count(r) AS relations
            """,
            {"lab": lab},
        )[0]
        by_type = run_cypher(
            """
            MATCH (n {lab: $lab})
            RETURN coalesce(n.entityType, labels(n)[0]) AS typ, count(*) AS cnt
            ORDER BY cnt DESC
            """,
            {"lab": lab},
        )
        print(f"  entities={overview['entities']} relations={overview['relations']}")
        print("  byType:", {r["typ"]: r["cnt"] for r in by_type})

        print("\n【行业覆盖】")
        for row in run_cypher(
            """
            MATCH (c:Company {lab: $lab})-[:BELONGS_TO]->(i:Industry {lab: $lab})
            RETURN i.name AS industry, count(c) AS companies
            ORDER BY companies DESC
            """,
            {"lab": lab},
        ):
            print(f"  {row['industry']}: {row['companies']} 家")

        print("\n【关系类型直方图】")
        for row in run_cypher(
            """
            MATCH ()-[r {lab: $lab}]->()
            RETURN type(r) AS rel, count(*) AS cnt
            ORDER BY cnt DESC
            """,
            {"lab": lab},
        ):
            print(f"  {row['rel']}: {row['cnt']}")

        print("\n【平均度数】")
        deg = run_cypher(
            """
            MATCH (n {lab: $lab})
            OPTIONAL MATCH (n)-[r {lab: $lab}]-()
            WITH n, count(r) AS d
            RETURN avg(d) AS avg_degree
            """,
            {"lab": lab},
        )[0]
        print(f"  {deg['avg_degree']:.2f}")

        print("\n【质量缺口】有公司无行业 / 无代码")
        gaps = run_cypher(
            """
            MATCH (c:Company {lab: $lab})
            OPTIONAL MATCH (c)-[:BELONGS_TO]->(i:Industry {lab: $lab})
            OPTIONAL MATCH (c)-[:LISTED_AS]->(s:Stock {lab: $lab})
            RETURN
              collect(DISTINCT CASE WHEN i IS NULL THEN c.name END) AS missing_industry,
              collect(DISTINCT CASE WHEN s IS NULL AND coalesce(c.listed,true) THEN c.name END) AS missing_code
            """,
            {"lab": lab},
        )[0]
        mi = [x for x in gaps["missing_industry"] if x]
        mc = [x for x in gaps["missing_code"] if x]
        print(f"  缺行业: {mi or '无'}")
        print(f"  缺代码: {mc or '无'}")

    print("\n互补：行情/财务进数仓；关系/事件进图谱。")


if __name__ == "__main__":
    demo()
