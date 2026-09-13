#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
学习小点：图数据库（Graph Database）
一句话：以「节点 + 边」原生存图，查询围绕遍历与模式匹配。

对应笔记：docs/3-知识存储.html → 图数据库
对比：关系库用 JOIN 算关联；图库把关联「存进去」。
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


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
    """
    属性图三要素：
      1. 节点 Node：可有多个 Label
      2. 关系 Relationship：有向、有 Type
      3. 属性 Property：挂在点或边上
    """

    def __init__(self) -> None:
        self.nodes: Dict[str, Node] = {}
        self.edges: Dict[str, Edge] = {}
        self._out: Dict[str, List[str]] = defaultdict(list)  # node -> edge ids

    def add_node(self, node_id: str, labels: List[str], **props: Any) -> Node:
        n = Node(node_id, labels, props)
        self.nodes[node_id] = n
        return n

    def add_edge(self, edge_id: str, typ: str, start: str, end: str, **props: Any) -> Edge:
        if start not in self.nodes or end not in self.nodes:
            raise KeyError("边的两端必须先存在")
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
        """多跳遍历：模拟 Cypher 的 [:TYPE*1..N]。"""
        paths: List[List[str]] = []

        def dfs(cur: str, path: List[str], depth: int) -> None:
            if depth > 0:
                paths.append(path[:])
            if depth == max_depth:
                return
            for e, nxt in self.neighbors(cur, edge_type):
                if nxt.id in path:  # 简单防环
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


def demo() -> None:
    print("=" * 60)
    print("图数据库学习脚本：属性图 + 多跳")
    print("=" * 60)

    g = build_demo_graph()
    moutai = g.nodes["c1"]
    print(f"\n【节点】{moutai.labels} {moutai.props}")

    print("\n【一跳出边】")
    for e, n in g.neighbors("c1"):
        print(f"  -[{e.type} {e.props}]-> {n.props or n.id} {n.labels}")

    print("\n【多跳 CONTROLS*1..2 从茅台集团出发】")
    for path in g.multi_hop("h1", "CONTROLS", 2):
        names = [g.nodes[i].props.get("name", i) for i in path]
        print("  " + " → ".join(names))

    print("\n选型口诀：多跳关联为主 → 优先图库；强 OWL 推理 → 考虑 RDF 库。")


if __name__ == "__main__":
    demo()
