#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
学习小点：本体匹配（Ontology Matching / Schema Matching）
一句话：在不同模式之间建立概念/关系对应，让数据能互相翻译。

对应笔记：docs/5-知识融合.html → 本体匹配
实体对齐 = 实例层同指；本体匹配 = 模式层同义。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass
class Schema:
    name: str
    classes: List[str]
    relations: List[str]  # 关系名
    attributes: List[str]


def token_set(name: str) -> set:
    # 拆 CamelCase / 下划线 / 中英文粗分
    import re

    parts = re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?=[A-Z]|$)|[\u4e00-\u9fff]+", name)
    if not parts:
        parts = [name.lower()]
    return {p.lower() for p in parts}


# 同义词表：匹配时常需要领域词典
SYNONYMS = {
    "corp": "company",
    "corporation": "company",
    "company": "company",
    "ticker": "stock",
    "stock": "stock",
    "listedcode": "listed_as",
    "listed_as": "listed_as",
    "listedas": "listed_as",
    "sector": "industry",
    "industry": "industry",
    "控股": "controls",
    "controls": "controls",
}


def canonical(term: str) -> str:
    t = "".join(ch for ch in term.lower() if ch.isalnum() or "\u4e00" <= ch <= "\u9fff")
    return SYNONYMS.get(t, t)


def match_terms(a: str, b: str) -> float:
    ca, cb = canonical(a), canonical(b)
    if ca == cb:
        return 1.0
    sa, sb = token_set(a), token_set(b)
    sa = {canonical(x) for x in sa}
    sb = {canonical(x) for x in sb}
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def match_schemas(src: Schema, tgt: Schema, threshold: float = 0.5) -> Dict[str, List[Tuple[str, str, float]]]:
    """输出类/关系/属性的对应候选。"""
    result = {"class": [], "relation": [], "attribute": []}
    pairs = [
        ("class", src.classes, tgt.classes),
        ("relation", src.relations, tgt.relations),
        ("attribute", src.attributes, tgt.attributes),
    ]
    for kind, left, right in pairs:
        for x in left:
            best = max(((y, match_terms(x, y)) for y in right), key=lambda t: t[1])
            if best[1] >= threshold:
                result[kind].append((x, best[0], best[1]))
    return result


def demo() -> None:
    print("=" * 60)
    print("本体匹配学习脚本：跨模式翻译")
    print("=" * 60)

    source_a = Schema(
        name="系统A",
        classes=["Corp", "Ticker", "Sector"],
        relations=["listedCode", "控股"],
        attributes=["证券代码", "corpName"],
    )
    source_b = Schema(
        name="系统B（本项目本体）",
        classes=["Company", "Stock", "Industry"],
        relations=["LISTED_AS", "CONTROLS"],
        attributes=["code", "name"],
    )

    print(f"\n【{source_a.name}】→【{source_b.name}】")
    mapping = match_schemas(source_a, source_b)
    for kind, rows in mapping.items():
        print(f"\n  {kind}:")
        for x, y, sc in rows:
            print(f"    {x}  ≡  {y}   ({sc:.2f})")

    print("\n落地：匹配结果可写成映射表，ETL 时把源字段翻译成统一本体再入库。")
    print("速记：先对齐模式，再对齐实例，否则「同名不同义」会污染融合。")


if __name__ == "__main__":
    demo()
