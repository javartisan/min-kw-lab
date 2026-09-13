#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
学习小点：KBQA（Knowledge Base Question Answering）
一句话：答案必须能在图上指出证据；图谱是真相来源。

对应笔记：docs/6-知识问答.html → KBQA
流水线：实体链接 → 意图识别 → 查图 → 答案+证据。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


# 迷你知识库（本应来自 Neo4j）
KG = {
    "entities": {
        "贵州茅台": {"type": "Company", "aliases": ["茅台"]},
        "白酒": {"type": "Industry", "aliases": []},
        "600519": {"type": "Stock", "aliases": []},
        "丁雄军": {"type": "Person", "aliases": []},
        "五粮液": {"type": "Company", "aliases": []},
    },
    "triples": [
        ("贵州茅台", "BELONGS_TO", "白酒"),
        ("贵州茅台", "LISTED_AS", "600519"),
        ("贵州茅台", "HAS_EXECUTIVE", "丁雄军"),
        ("贵州茅台", "COMPETES_WITH", "五粮液"),
        ("五粮液", "BELONGS_TO", "白酒"),
    ],
}


@dataclass
class Answer:
    value: str
    evidence: List[Tuple[str, str, str]]
    note: str = ""


def link_entity(question: str) -> Optional[str]:
    """实体链接：问句中的提及 → 标准节点名。"""
    # 长别名优先
    candidates = []
    for name, meta in KG["entities"].items():
        for alias in [name, *meta["aliases"]]:
            if alias in question:
                candidates.append((len(alias), name))
    if not candidates:
        return None
    candidates.sort(reverse=True)
    return candidates[0][1]


def detect_intent(question: str) -> Optional[str]:
    """意图识别：问的是什么关系/属性。"""
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


def query_kg(entity: str, relation: str) -> List[Tuple[str, str, str]]:
    return [t for t in KG["triples"] if t[0] == entity and t[1] == relation]


def answer(question: str) -> Answer:
    entity = link_entity(question)
    if not entity:
        return Answer("图谱暂无", [], "实体链接失败")
    intent = detect_intent(question)
    if not intent:
        return Answer("图谱暂无", [], "未识别意图")
    hits = query_kg(entity, intent)
    if not hits:
        return Answer("图谱暂无", [], f"无 {entity}-{intent} 事实")
    values = "、".join(t[2] for t in hits)
    return Answer(values, hits, "OK")


def demo() -> None:
    print("=" * 60)
    print("KBQA 学习脚本：问句 → 图上证据 → 答案")
    print("=" * 60)

    questions = [
        "茅台的股票代码是什么？",
        "贵州茅台属于什么行业？",
        "贵州茅台的董事长是谁？",
        "和贵州茅台竞争的公司有哪些？",
        "今天天气怎么样？",  # 应拒答
    ]

    for q in questions:
        a = answer(q)
        print(f"\nQ: {q}")
        print(f"A: {a.value}  ({a.note})")
        for e in a.evidence:
            print(f"   证据: {e}")

    print("\n与纯 LLM 差别：KBQA 无结果就说「库中无」，不编造董事长。")


if __name__ == "__main__":
    demo()
