#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
学习小点：语义解析 → 真实执行 Cypher
一句话：把自然语言「编译」成参数化 Cypher，再在 Neo4j 上跑。

对应笔记：docs/6-知识问答.html → 语义解析
工程要点：模板槽位可控；LLM 生成须校验只读后再执行。
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from common.neo4j_client import get_lab_tag, require_neo4j, run_cypher
from common.seed_kg import ensure_seed_graph

ALIAS = {"茅台": "贵州茅台", "宁德": "宁德时代"}

# template_id, pattern, cypher（一律带 lab + $name）
TEMPLATES: List[Tuple[str, str, str]] = [
    (
        "stock_code",
        r"(.+?)的?股票代码",
        """
        MATCH (c:Company {name: $name, lab: $lab})-[:LISTED_AS]->(s:Stock)
        RETURN s.name AS answer
        """,
    ),
    (
        "industry",
        r"(.+?)属于什么行业",
        """
        MATCH (c:Company {name: $name, lab: $lab})-[:BELONGS_TO]->(i:Industry)
        RETURN i.name AS answer
        """,
    ),
    (
        "executive",
        r"(.+?)的董事长是谁",
        """
        MATCH (c:Company {name: $name, lab: $lab})-[:HAS_EXECUTIVE]->(p:Person)
        RETURN p.name AS answer
        """,
    ),
    (
        "competitor",
        r"和(.+?)竞争的公司有哪些",
        """
        MATCH (c:Company {name: $name, lab: $lab})-[:COMPETES_WITH]-(x:Company)
        RETURN DISTINCT x.name AS answer
        """,
    ),
]


@dataclass
class ParsedQuery:
    cypher: str
    params: Dict[str, str]
    template_id: str


def normalize_entity(raw: str) -> str:
    name = raw.strip().rstrip("？?的")
    return ALIAS.get(name, name)


def parse(question: str) -> Optional[ParsedQuery]:
    q = question.strip().rstrip("？?")
    for tid, pattern, cypher in TEMPLATES:
        m = re.search(pattern, q)
        if m:
            return ParsedQuery(
                cypher=cypher,
                params={"name": normalize_entity(m.group(1))},
                template_id=tid,
            )
    return None


def validate_readonly(cypher: str) -> bool:
    banned = ["DELETE", "DETACH", "DROP", "CREATE", "MERGE", "SET", "LOAD CSV", "CALL"]
    upper = cypher.upper()
    return not any(b in upper for b in banned)


def demo() -> None:
    print("=" * 60)
    print("语义解析：NL → Cypher → Neo4j 执行")
    print("=" * 60)

    questions = [
        "茅台的股票代码？",
        "贵州茅台属于什么行业？",
        "宁德时代的董事长是谁？",
        "和贵州茅台竞争的公司有哪些？",
    ]

    with require_neo4j():
        ensure_seed_graph(reset=False)
        lab = get_lab_tag()
        for q in questions:
            pq = parse(q)
            print(f"\nQ: {q}")
            if not pq:
                print("  无法解析")
                continue
            print(f"  template={pq.template_id}  params={pq.params}")
            print(f"  只读校验: {validate_readonly(pq.cypher)}")
            if not validate_readonly(pq.cypher):
                print("  拒绝执行")
                continue
            rows = run_cypher(pq.cypher, {**pq.params, "lab": lab})
            answers = [r["answer"] for r in rows]
            print(f"  Neo4j 结果: {answers or ['（空）']}")


if __name__ == "__main__":
    demo()
