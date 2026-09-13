#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
学习小点：语义解析（Semantic Parsing → 图查询）
一句话：把自然语言「编译」成 Cypher / SPARQL。

对应笔记：docs/6-知识问答.html → 语义解析
工程三条路：模板槽位 / 解析模型 / LLM 生成（需校验）。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple


@dataclass
class ParsedQuery:
    cypher: str
    params: Dict[str, str]
    template_id: str


# 模板：正则抽槽 → 固定 Cypher（可控、适合证券高频问法）
TEMPLATES: List[Tuple[str, str, str]] = [
    # template_id, pattern, cypher
    (
        "stock_code",
        r"(.+?)的?股票代码",
        "MATCH (c:Company {name: $name})-[:LISTED_AS]->(s:Stock)\n"
        "RETURN s.code AS answer",
    ),
    (
        "industry",
        r"(.+?)属于什么行业",
        "MATCH (c:Company {name: $name})-[:BELONGS_TO]->(i:Industry)\n"
        "RETURN i.name AS answer",
    ),
    (
        "executive",
        r"(.+?)的董事长是谁",
        "MATCH (c:Company {name: $name})-[:HAS_EXECUTIVE]->(p:Person)\n"
        "RETURN p.name AS answer",
    ),
    (
        "competitor",
        r"和(.+?)竞争的公司有哪些",
        "MATCH (c:Company {name: $name})-[:COMPETES_WITH]-(x:Company)\n"
        "RETURN DISTINCT x.name AS answer",
    ),
]


ALIAS = {"茅台": "贵州茅台", "宁德": "宁德时代"}


def normalize_entity(raw: str) -> str:
    name = raw.strip().rstrip("？?的")
    return ALIAS.get(name, name)


def parse(question: str) -> Optional[ParsedQuery]:
    q = question.strip().rstrip("？?")
    for tid, pattern, cypher in TEMPLATES:
        m = re.fullmatch(pattern, q)
        if not m:
            # 允许句末语气词等：用 search
            m = re.search(pattern, q)
        if m:
            name = normalize_entity(m.group(1))
            return ParsedQuery(cypher=cypher, params={"name": name}, template_id=tid)
    return None


def fake_execute(pq: ParsedQuery) -> List[str]:
    """用字典冒充 Neo4j 执行结果。"""
    db = {
        ("贵州茅台", "stock_code"): ["600519"],
        ("贵州茅台", "industry"): ["白酒"],
        ("贵州茅台", "executive"): ["丁雄军"],
        ("贵州茅台", "competitor"): ["五粮液"],
        ("宁德时代", "executive"): ["曾毓群"],
    }
    return db.get((pq.params["name"], pq.template_id), [])


def validate_cypher(cypher: str) -> bool:
    """LLM 生成查询时的最小护栏：只读 + 禁危险关键字。"""
    banned = ["DELETE", "DETACH", "DROP", "CREATE", "MERGE", "SET", "LOAD CSV"]
    upper = cypher.upper()
    if not upper.lstrip().startswith("MATCH") and "RETURN" not in upper:
        return False
    return not any(b in upper for b in banned)


def demo() -> None:
    print("=" * 60)
    print("语义解析学习脚本：NL → Cypher")
    print("=" * 60)

    questions = [
        "茅台的股票代码？",
        "贵州茅台属于什么行业？",
        "宁德时代的董事长是谁？",
        "和贵州茅台竞争的公司有哪些？",
    ]

    for q in questions:
        pq = parse(q)
        print(f"\nQ: {q}")
        if not pq:
            print("  无法解析")
            continue
        print(f"  template={pq.template_id}  params={pq.params}")
        print("  Cypher:")
        for line in pq.cypher.splitlines():
            print(f"    {line}")
        print(f"  校验只读: {validate_cypher(pq.cypher)}")
        print(f"  执行结果: {fake_execute(pq)}")

    print("\n安全：参数化绑定 $name；LLM 出的 Cypher 先校验再执行。")


if __name__ == "__main__":
    demo()
