#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
学习小点：RE（Relation Extraction，关系抽取）
一句话：判定两个实体之间是什么语义关系，输出三元组。

对应笔记：docs/2-知识获取.html → RE
前提：通常先有 NER 的实体列表。
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import List, Optional, Tuple


@dataclass
class Entity:
    text: str
    type: str
    start: int
    end: int


@dataclass
class Relation:
    head: Entity
    relation: str
    tail: Entity
    evidence: str  # 触发该关系的文本片段，便于解释


# 类型约束：只有符合本体的实体对才允许尝试某些关系
ALLOWED: dict[str, Tuple[str, str]] = {
    "BELONGS_TO": ("Company", "Industry"),
    "LISTED_AS": ("Company", "Stock"),
    "HAS_EXECUTIVE": ("Company", "Person"),
    "COMPETES_WITH": ("Company", "Company"),
}


def classify_pair(sentence: str, e1: Entity, e2: Entity) -> Optional[Relation]:
    """
    模板/关键词分类器（规则路线）。
    真实系统可用：依存句法、远程监督、BERT 分类、LLM。
    """
    # 用两实体的局部窗口，避免整句噪声干扰证据展示
    left, right = (e1, e2) if e1.start <= e2.start else (e2, e1)
    local = sentence[max(0, left.start - 2) : min(len(sentence), right.end + 6)]

    candidates: List[Tuple[str, Entity, Entity, str]] = []

    # 关键词 → 关系假设，再校验类型
    rules = [
        (("属于", "行业"), "BELONGS_TO"),
        (("代码", "股票"), "LISTED_AS"),
        (("董事长", "总经理", "任职", "任"), "HAS_EXECUTIVE"),
        (("竞争", "对标", "竞品"), "COMPETES_WITH"),
    ]

    for keys, rel in rules:
        if not any(k in local for k in keys):
            continue
        domain, range_ = ALLOWED[rel]
        for head, tail in ((e1, e2), (e2, e1)):
            if head.type == domain and tail.type == range_:
                hit = next(k for k in keys if k in local)
                candidates.append((rel, head, tail, hit))

    if not candidates:
        return None
    rel, head, tail, ev = candidates[0]
    return Relation(head, rel, tail, ev)


def extract_relations(sentence: str, entities: List[Entity]) -> List[Relation]:
    """对句子中所有实体对做关系分类。"""
    results: List[Relation] = []
    for e1, e2 in combinations(entities, 2):
        rel = classify_pair(sentence, e1, e2)
        if rel:
            results.append(rel)
    return results


def demo() -> None:
    print("=" * 60)
    print("RE 学习脚本：实体对 → 关系三元组")
    print("=" * 60)

    sentence = "贵州茅台属于白酒行业，丁雄军任贵州茅台董事长。"
    # 假设 NER 已完成
    entities = [
        Entity("贵州茅台", "Company", 0, 4),
        Entity("白酒", "Industry", 6, 8),
        Entity("丁雄军", "Person", 11, 14),
    ]
    # 修正「丁雄军」位置（上面 start 是示意；下面按真实 find）
    entities = []
    for name, typ in [("贵州茅台", "Company"), ("白酒", "Industry"), ("丁雄军", "Person")]:
        i = sentence.find(name)
        entities.append(Entity(name, typ, i, i + len(name)))

    print(f"\n【句子】{sentence}")
    print("【实体】", [f"{e.text}/{e.type}" for e in entities])

    rels = extract_relations(sentence, entities)
    print("\n【关系】")
    for r in rels:
        print(
            f"  ({r.head.text}) -[{r.relation}]-> ({r.tail.text})"
            f"  证据={r.evidence!r}"
        )

    print("\n速记：RE 必须受本体约束——Company 才能 BELONGS_TO Industry。")


if __name__ == "__main__":
    demo()
