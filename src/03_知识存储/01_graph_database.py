#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
学习小点：图数据库（属性图模型 + Neo4j 对照）
一句话：以「节点 + 边」原生存图；真实工程用 Neo4j 持久化与多跳查询。

对应笔记：docs/3-知识存储.html → 图数据库
本脚本：先讲清内存属性图模型，再对同一问题跑 Neo4j Cypher（需手动启动库）。
"""

from __future__ import annotations

import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from common.neo4j_client import get_lab_tag, require_neo4j, run_cypher
from common.seed_kg import ensure_seed_graph


@dataclass
class Node:
    id: str
    labels: List[str]
    props: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Edge:
    id: str
    type: str
    start: str
    end: str
    props: Dict[str, Any] = field(default_factory=dict)


class PropertyGraph:
    """内存属性图：帮助理解 Node / Rel / Property，不替代真实图库。"""

    def __init__(self) -> None:
        self.nodes: Dict[str, Node] = {}
        self.edges: Dict[str, Edge] = {}
        self._out: Dict[str, List[str]] = defaultdict(list)

    def add_node(self, node_id: str, labels: List[str], **props: Any) -> Node:
        n = Node(node_id, labels, props)
        self.nodes[node_id] = n
        return n

    def add_edge(self, edge_id: str, typ: str, start: str, end: str, **props: Any) -> Edge:
        e = Edge(edge_id, typ, start, end, props)
        self.edges[edge_id] = e
        self._out[start].append(edge_id)
        return e

    def neighbors(self, node_id: str, edge_type: Optional[str] = None) -> List[Tuple[Edge, Node]]:
        result = []
        for eid in self._out[node_id]:
            e = self.edges[eid]
            if edge_type and e.type != edge_type:
                continue
            result.append((e, self.nodes[e.end]))
        return result

    def multi_hop(self, start: str, edge_type: str, max_depth: int) -> List[List[str]]:
        paths: List[List[str]] = []

        def dfs(cur: str, path: List[str], depth: int) -> None:
            if depth > 0:
                paths.append(path[:])
            if depth == max_depth:
                return
            for e, nxt in self.neighbors(cur, edge_type):
                if nxt.id in path:
                    continue
                path.append(nxt.id)
                dfs(nxt.id, path, depth + 1)
                path.pop()

        dfs(start, [start], 0)
        return paths


def build_demo_graph() -> PropertyGraph:
    g = PropertyGraph()
    g.add_node("c1", ["Company", "ListedCompany"], name="贵州茅台")
    g.add_node("s1", ["Stock"], code="600519")
    g.add_node("i1", ["Industry"], name="白酒")
    g.add_node("c2", ["Company"], name="五粮液")
    g.add_node("h1", ["Company"], name="茅台集团")
    g.add_edge("e1", "LISTED_AS", "c1", "s1")
    g.add_edge("e2", "BELONGS_TO", "c1", "i1")
    g.add_edge("e3", "BELONGS_TO", "c2", "i1")
    g.add_edge("e4", "COMPETES_WITH", "c1", "c2")
    g.add_edge("e5", "CONTROLS", "h1", "c1", ratio=0.54)
    return g


def demo_in_memory() -> None:
    print("\n── 内存属性图（理解模型）──")
    g = build_demo_graph()
    moutai = g.nodes["c1"]
    print(f"节点: {moutai.labels} {moutai.props}")
    print("一跳出边:")
    for e, n in g.neighbors("c1"):
        print(f"  -[{e.type}]-> {n.props or n.id}")
    print("多跳 CONTROLS 从茅台集团:")
    for path in g.multi_hop("h1", "CONTROLS", 2):
        names = [g.nodes[i].props.get("name", i) for i in path]
        print("  " + " → ".join(names))


def demo_neo4j() -> None:
    print("\n── Neo4j 对照（真实多跳）──")
    lab = get_lab_tag()
    with require_neo4j():
        stats = ensure_seed_graph(reset=False)
        print(f"种子: nodes={stats['nodes']} rels={stats['rels']}")

        rows = run_cypher(
            """
            MATCH (c:Company {name: $name, lab: $lab})-[r]->(n {lab: $lab})
            RETURN type(r) AS rel, labels(n) AS labels, n.name AS name
            ORDER BY rel
            """,
            {"name": "贵州茅台", "lab": lab},
        )
        print("贵州茅台一跳出边:")
        for row in rows:
            print(f"  -[{row['rel']}]-> {row['name']} {row['labels']}")

        paths = run_cypher(
            """
            MATCH path = (a:Company {name: $name, lab: $lab})
                         -[:CONTROLS*1..2]->(b {lab: $lab})
            RETURN [n IN nodes(path) | n.name] AS names
            """,
            {"name": "茅台集团", "lab": lab},
        )
        print("CONTROLS*1..2:")
        for row in paths:
            print("  " + " → ".join(row["names"]))


def demo() -> None:
    print("=" * 60)
    print("图数据库：内存模型 + Neo4j 工程对照")
    print("=" * 60)
    demo_in_memory()
    demo_neo4j()
    print("\n选型：多跳关联为主 → 优先图库；本项目学习落点 = Neo4j。")


if __name__ == "__main__":
    demo()
