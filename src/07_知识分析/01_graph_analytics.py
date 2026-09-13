#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
学习小点：图分析（Graph Analytics）
一句话：中心性、路径、社区、结构相似 —— 挖「谁重要、谁一伙、怎么连」。

对应笔记：docs/7-知识分析.html → 图分析
"""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Dict, List, Optional, Set, Tuple


class SimpleGraph:
    def __init__(self) -> None:
        self.adj: Dict[str, Set[str]] = defaultdict(set)  # 无向化，便于中心性 demo
        self.typed: List[Tuple[str, str, str]] = []

    def add(self, s: str, rel: str, o: str) -> None:
        self.typed.append((s, rel, o))
        self.adj[s].add(o)
        self.adj[o].add(s)

    def degree_centrality(self) -> List[Tuple[str, int]]:
        """度中心性：连接越多越「枢纽」。"""
        scored = [(n, len(neis)) for n, neis in self.adj.items()]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored

    def shortest_path(self, src: str, dst: str) -> Optional[List[str]]:
        """BFS 最短路径：股权穿透/关联路径的入门版。"""
        if src not in self.adj or dst not in self.adj:
            return None
        prev = {src: None}
        q = deque([src])
        while q:
            cur = q.popleft()
            if cur == dst:
                break
            for nxt in self.adj[cur]:
                if nxt not in prev:
                    prev[nxt] = cur
                    q.append(nxt)
        if dst not in prev:
            return None
        path = [dst]
        while path[-1] != src:
            path.append(prev[path[-1]])  # type: ignore
        path.reverse()
        return path

    def common_neighbors_similarity(self, a: str, b: str) -> float:
        """结构相似：共同邻居越多越像（对标/竞品候选）。"""
        na, nb = self.adj[a], self.adj[b]
        if not na or not nb:
            return 0.0
        return len(na & nb) / len(na | nb)


def connected_components(g: SimpleGraph) -> List[List[str]]:
    """社区发现的最简替代：连通分量（真实可用 Louvain 等）。"""
    seen: Set[str] = set()
    comps: List[List[str]] = []
    for node in g.adj:
        if node in seen:
            continue
        comp = []
        stack = [node]
        while stack:
            x = stack.pop()
            if x in seen:
                continue
            seen.add(x)
            comp.append(x)
            stack.extend(g.adj[x] - seen)
        comps.append(sorted(comp))
    return comps


def demo() -> None:
    print("=" * 60)
    print("图分析学习脚本：度中心性 / 最短路径 / 相似 / 连通分量")
    print("=" * 60)

    g = SimpleGraph()
    edges = [
        ("茅台集团", "CONTROLS", "贵州茅台"),
        ("贵州茅台", "BELONGS_TO", "白酒"),
        ("五粮液", "BELONGS_TO", "白酒"),
        ("贵州茅台", "COMPETES_WITH", "五粮液"),
        ("宁德时代", "BELONGS_TO", "动力电池"),
        ("某材料公司", "SUPPLIES", "宁德时代"),
    ]
    for e in edges:
        g.add(*e)

    print("\n【度中心性 Top】")
    for n, d in g.degree_centrality()[:5]:
        print(f"  {n:8s}  degree={d}")

    print("\n【路径】茅台集团 → 五粮液")
    print(" ", " → ".join(g.shortest_path("茅台集团", "五粮液") or ["不可达"]))

    print("\n【结构相似】贵州茅台 vs 五粮液 / 宁德时代")
    print(f"  vs 五粮液: {g.common_neighbors_similarity('贵州茅台', '五粮液'):.2f}")
    print(f"  vs 宁德时代: {g.common_neighbors_similarity('贵州茅台', '宁德时代'):.2f}")

    print("\n【连通分量≈粗社区】")
    for i, c in enumerate(connected_components(g), 1):
        print(f"  社区{i}: {c}")

    print("\n分析结果可回写为节点属性（pagerank、communityId）供问答过滤。")


if __name__ == "__main__":
    demo()
