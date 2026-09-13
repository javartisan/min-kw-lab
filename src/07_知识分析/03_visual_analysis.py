#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
学习小点：可视化分析
一句话：把子图变成可探索的视图——下钻、过滤、叙事展示。

对应笔记：docs/7-知识分析.html → 可视化分析
本脚本输出：终端 ASCII 图 + 一份可被前端/Gephi 使用的 JSON。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple


Triple = Tuple[str, str, str]

GRAPH: List[Triple] = [
    ("茅台集团", "CONTROLS", "贵州茅台"),
    ("贵州茅台", "LISTED_AS", "600519"),
    ("贵州茅台", "BELONGS_TO", "白酒"),
    ("贵州茅台", "COMPETES_WITH", "五粮液"),
    ("五粮液", "BELONGS_TO", "白酒"),
    ("贵州茅台", "HAS_EXECUTIVE", "丁雄军"),
]


NODE_TYPE = {
    "茅台集团": "Company",
    "贵州茅台": "Company",
    "五粮液": "Company",
    "600519": "Stock",
    "白酒": "Industry",
    "丁雄军": "Person",
}


def subgraph_around(center: str) -> List[Triple]:
    """下钻：只看与中心实体直接相连的边。"""
    return [t for t in GRAPH if t[0] == center or t[2] == center]


def to_viz_json(triples: List[Triple]) -> Dict[str, Any]:
    """
    常见前端格式（nodes + links），可被 D3 / ECharts / 自研画布消费。
    """
    nodes: Dict[str, Dict[str, str]] = {}
    links = []
    for s, p, o in triples:
        for n in (s, o):
            nodes[n] = {"id": n, "type": NODE_TYPE.get(n, "Unknown")}
        links.append({"source": s, "target": o, "type": p})
    return {"nodes": list(nodes.values()), "links": links}


def ascii_view(triples: List[Triple], center: str) -> str:
    """终端叙事视图：以中心实体为枢纽列出关系。"""
    lines = [f"[{center}]", "  |"]
    for s, p, o in triples:
        if s == center:
            lines.append(f"  +--[{p}]--> {o} ({NODE_TYPE.get(o, '?')})")
        else:
            lines.append(f"  +--[{p}]--< {s} ({NODE_TYPE.get(s, '?')})")
    return "\n".join(lines)


def filter_by_rel_types(triples: List[Triple], allowed: Set[str]) -> List[Triple]:
    """可视化过滤：只显示关心的边类型（如股权+上市）。"""
    return [t for t in triples if t[1] in allowed]


def demo() -> None:
    print("=" * 60)
    print("可视化分析学习脚本：下钻 / 过滤 / 导出 JSON")
    print("=" * 60)

    center = "贵州茅台"
    sub = subgraph_around(center)

    print("\n【交互下钻 · ASCII】")
    print(ascii_view(sub, center))

    print("\n【过滤：只看 CONTROLS + LISTED_AS】")
    focused = filter_by_rel_types(GRAPH, {"CONTROLS", "LISTED_AS"})
    for t in focused:
        print(f"  {t}")

    payload = to_viz_json(sub)
    out = Path(__file__).with_name("viz_subgraph.json")
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n【已导出】{out.name}  (nodes={len(payload['nodes'])}, links={len(payload['links'])})")
    print(json.dumps(payload, ensure_ascii=False, indent=2))

    print("\n叙事建议：先总览指标 → 再下钻关键公司子图 → 用路径讲清关联。")


if __name__ == "__main__":
    demo()
