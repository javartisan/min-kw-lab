#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
学习小点：KBQA（查真实 Neo4j）
一句话：答案必须能在图上指出证据；图谱是真相来源。

对应笔记：docs/6-知识问答.html → KBQA
工程流水线：实体链接 → 意图 → 参数化 Cypher → 答案+证据边。
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from common.neo4j_client import get_lab_tag, require_neo4j, run_cypher
from common.seed_kg import ensure_seed_graph

# 别名 → 标准节点名（工程里常来自别名词表 / 实体链接服务）
ALIASES = {
    "茅台": "贵州茅台",
    "贵州茅台": "贵州茅台",
    "五粮液": "五粮液",
    "宁德时代": "宁德时代",
    "宁德": "宁德时代",
}

INTENT_CYPHER = {
    "LISTED_AS": """
        MATCH (c {name: $name, lab: $lab})-[r:LISTED_AS]->(s)
        RETURN s.name AS answer, c.name AS subj, type(r) AS rel, s.name AS obj
        """,
    "BELONGS_TO": """
        MATCH (c {name: $name, lab: $lab})-[r:BELONGS_TO]->(i)
        RETURN i.name AS answer, c.name AS subj, type(r) AS rel, i.name AS obj
        """,
    "HAS_EXECUTIVE": """
        MATCH (c {name: $name, lab: $lab})-[r:HAS_EXECUTIVE]->(p)
        RETURN p.name AS answer, c.name AS subj, type(r) AS rel, p.name AS obj
        """,
    "COMPETES_WITH": """
        MATCH (c {name: $name, lab: $lab})-[r:COMPETES_WITH]-(x)
        RETURN x.name AS answer, c.name AS subj, type(r) AS rel, x.name AS obj
        """,
}


@dataclass
class Answer:
    value: str
    evidence: List[Tuple[str, str, str]]
    note: str = ""


def link_entity(question: str) -> Optional[str]:
    hits = [(len(alias), name) for alias, name in ALIASES.items() if alias in question]
    if not hits:
        return None
    hits.sort(reverse=True)
    return hits[0][1]


def detect_intent(question: str) -> Optional[str]:
    mapping = [
        (("代码", "股票代码"), "LISTED_AS"),
        (("行业", "属于什么"), "BELONGS_TO"),
        (("董事长", "高管", "谁任"), "HAS_EXECUTIVE"),
        (("竞争", "竞品"), "COMPETES_WITH"),
    ]
    for keys, intent in mapping:
        if any(k in question for k in keys):
            return intent
    return None


def answer(question: str) -> Answer:
    entity = link_entity(question)
    if not entity:
        return Answer("图谱暂无", [], "实体链接失败")
    intent = detect_intent(question)
    if not intent:
        return Answer("图谱暂无", [], "未识别意图")

    lab = get_lab_tag()
    rows = run_cypher(INTENT_CYPHER[intent], {"name": entity, "lab": lab})
    if not rows:
        return Answer("图谱暂无", [], f"无 {entity}-{intent} 事实")

    values = "、".join(dict.fromkeys(r["answer"] for r in rows))
    evidence = [(r["subj"], r["rel"], r["obj"]) for r in rows]
    return Answer(values, evidence, "OK · Neo4j")


def demo() -> None:
    print("=" * 60)
    print("KBQA：自然语言 → Neo4j 证据 → 答案")
    print("=" * 60)

    questions = [
        "茅台的股票代码是什么？",
        "贵州茅台属于什么行业？",
        "贵州茅台的董事长是谁？",
        "和贵州茅台竞争的公司有哪些？",
        "今天天气怎么样？",
    ]

    with require_neo4j():
        ensure_seed_graph(reset=False)
        for q in questions:
            a = answer(q)
            print(f"\nQ: {q}")
            print(f"A: {a.value}  ({a.note})")
            for e in a.evidence:
                print(f"   证据: {e}")

    print("\n与纯 LLM 差别：无边就说「库中无」，不编造。")


if __name__ == "__main__":
    demo()
