#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
学习小点：可视化分析（从 Neo4j 导出 nodes/links JSON）
一句话：下钻子图 → 过滤边类型 → 导出前端可消费的 JSON。

对应笔记：docs/7-知识分析.html → 可视化分析
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Set

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from common.neo4j_client import get_lab_tag, require_neo4j, run_cypher
from common.seed_kg import ensure_seed_graph


def fetch_ego(center: str) -> List[Dict[str, Any]]:
    lab = get_lab_tag()
    return run_cypher(
        """
        MATCH (c {name: $name, lab: $lab})-[r]-(n {lab: $lab})
        RETURN c.name AS center,
               type(r) AS rel,
               startNode(r).name AS start,
               endNode(r).name AS end,
               labels(startNode(r))[0] AS start_type,
               labels(endNode(r))[0] AS end_type
        """,
        {"name": center, "lab": lab},
    )


def to_viz_json(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    nodes: Dict[str, Dict[str, str]] = {}
    links = []
    for row in rows:
        nodes[row["start"]] = {"id": row["start"], "type": row["start_type"]}
        nodes[row["end"]] = {"id": row["end"], "type": row["end_type"]}
        links.append({"source": row["start"], "target": row["end"], "type": row["rel"]})
    return {"nodes": list(nodes.values()), "links": links}


def ascii_view(center: str, rows: List[Dict[str, Any]]) -> str:
    lines = [f"[{center}]", "  |"]
    for row in rows:
        if row["start"] == center:
            lines.append(
                f"  +--[{row['rel']}]--> {row['end']} ({row['end_type']})"
            )
        else:
            lines.append(
                f"  +--[{row['rel']}]--< {row['start']} ({row['start_type']})"
            )
    return "\n".join(lines)


def filter_rows(rows: List[Dict[str, Any]], allowed: Set[str]) -> List[Dict[str, Any]]:
    return [r for r in rows if r["rel"] in allowed]


def demo() -> None:
    print("=" * 60)
    print("可视化分析：Neo4j 下钻 / 过滤 / 导出 JSON")
    print("=" * 60)

    center = "贵州茅台"
    with require_neo4j():
        ensure_seed_graph(reset=False)
        rows = fetch_ego(center)

        print("\n【交互下钻 · ASCII】")
        print(ascii_view(center, rows))

        print("\n【过滤：只看 CONTROLS + LISTED_AS】")
        # 下钻结果可能不含 CONTROLS 入边方向——再查全局过滤示例
        lab = get_lab_tag()
        focused = run_cypher(
            """
            MATCH (a {lab: $lab})-[r:CONTROLS|LISTED_AS]->(b {lab: $lab})
            RETURN a.name AS a, type(r) AS rel, b.name AS b
            """,
            {"lab": lab},
        )
        for row in focused:
            print(f"  ({row['a']})-[{row['rel']}]->({row['b']})")

        payload = to_viz_json(rows)
        out = Path(__file__).with_name("viz_subgraph.json")
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(
            f"\n【已导出】{out.name}  "
            f"(nodes={len(payload['nodes'])}, links={len(payload['links'])})"
        )
        print(json.dumps(payload, ensure_ascii=False, indent=2))

    print("\n叙事：先指标总览 → 再下钻关键公司子图 → 用路径讲清关联。")


if __name__ == "__main__":
    demo()
