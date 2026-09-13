#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
学习小点：本体 / 模式对齐（Ontology Matching / Schema Matching）

一句话：不同系统对「同一概念」起了不同名字时，先建立模式对应，再翻译数据。

和「实体对齐」的差别（务必分清）：
  ┌────────────┬──────────────────────────┬─────────────────────────┐
  │            │ 本体/模式对齐             │ 实体对齐                 │
  ├────────────┼──────────────────────────┼─────────────────────────┤
  │ 对准什么   │ 类 / 关系 / 属性（模式）  │ 具体个体（实例）         │
  │ 例子       │ Corp ≡ Company           │ 茅台 ≡ Moutai           │
  │            │ listedCode ≡ LISTED_AS   │                         │
  │ 不做的事   │ 不管「是不是同一家公司」  │ 不管「Corp 是不是类名」  │
  └────────────┴──────────────────────────┴─────────────────────────┘

对应笔记：docs/5-知识融合.html → 本体匹配
运行：python src/05_知识融合/02_ontology_matching.py
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 1. 模式（Schema）= 一个数据源自己的「词典」
# ---------------------------------------------------------------------------

@dataclass
class Schema:
    """
    某个系统对外暴露的概念词典（不是具体茅台这种实例）。

    例子 — 行情源 A：
      classes    = ["Corp", "Ticker", "Sector"]
      relations  = ["listedCode", "控股"]
      attributes = ["证券代码", "corpName"]
    """

    name: str  # 数据源名称，如 "行情系统A"
    classes: List[str]  # 类/概念名
    relations: List[str]  # 关系/谓词名
    attributes: List[str]  # 数据属性/字段名


@dataclass
class SchemaMapping:
    """
    对齐结果：源模式术语 → 目标本体术语。

    工程落地时常落成配置表 / YAML，供 ETL 翻译时查表。
    """

    class_map: Dict[str, str] = field(default_factory=dict)  # Corp → Company
    relation_map: Dict[str, str] = field(default_factory=dict)  # listedCode → LISTED_AS
    attribute_map: Dict[str, str] = field(default_factory=dict)  # corpName → name
    scores: Dict[Tuple[str, str, str], float] = field(default_factory=dict)
    # scores 键：(层, 源术语, 目标术语) → 匹配分，便于审计


# ---------------------------------------------------------------------------
# 2. 术语规范化 + 相似度（匹配信号）
# ---------------------------------------------------------------------------

# 领域同义词表：匹配的「先验知识」，比纯字符串相似更稳
# 真实项目可来自：业务字典、WordNet、Embedding 近邻 + 人工确认
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
    "证券代码": "code",
    "code": "code",
    "corpname": "name",
    "name": "name",
}


def token_set(name: str) -> set[str]:
    """
    把标识符拆成词袋，便于部分匹配。

    例子：
      "listedCode" → {"listed", "code"}
      "LISTED_AS"  → {"listed", "as"}
      "证券代码"   → {"证券代码"}
    """
    parts = re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?=[A-Z]|$)|[\u4e00-\u9fff]+", name)
    if not parts:
        parts = [name.lower()]
    return {p.lower() for p in parts}


def canonical(term: str) -> str:
    """
    术语归一：去杂质 → 查同义词表 → 得到「概念指纹」。

    例子：
      "Corp"        → "company"
      "Corporation" → "company"
      "listedCode"  → "listed_as"
    """
    # 只保留字母数字和中文，统一小写
    t = "".join(ch for ch in term.lower() if ch.isalnum() or "\u4e00" <= ch <= "\u9fff")
    return SYNONYMS.get(t, t)


def match_terms(a: str, b: str) -> float:
    """
    两个模式术语有多像（0~1）。

    策略（由强到弱）：
      1) 归一后完全相同 → 1.0（Corp vs Company）
      2) 词袋 Jaccard（canonical 后）→ 部分重合也给分
    """
    ca, cb = canonical(a), canonical(b)
    if ca == cb:
        return 1.0  # 同义词命中：最强信号
    sa = {canonical(x) for x in token_set(a)}
    sb = {canonical(x) for x in token_set(b)}
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)  # Jaccard：交集 / 并集


# ---------------------------------------------------------------------------
# 3. 模式对齐：为源模式每个术语找目标本体里最像的那个
# ---------------------------------------------------------------------------

def match_schemas(
    src: Schema,
    tgt: Schema,
    threshold: float = 0.5,
) -> SchemaMapping:
    """
    在 src 与 tgt 之间建立类/关系/属性对应。

    算法（教学贪心）：
      对源侧每个术语，在目标侧同类术语中选 score 最高者；
      分数 ≥ threshold 才采纳（避免乱配）。

    返回：
      SchemaMapping，可直接拿去翻译实例三元组。
    """
    mapping = SchemaMapping()
    layers = [
        ("class", src.classes, tgt.classes, mapping.class_map),
        ("relation", src.relations, tgt.relations, mapping.relation_map),
        ("attribute", src.attributes, tgt.attributes, mapping.attribute_map),
    ]
    for kind, left, right, bucket in layers:
        for x in left:  # 源术语，如 "Corp"
            # 在目标列表里找得分最高的一项
            best_y, best_sc = max(
                ((y, match_terms(x, y)) for y in right),
                key=lambda t: t[1],
            )
            if best_sc >= threshold:  # 过阈值才写入映射
                bucket[x] = best_y
                mapping.scores[(kind, x, best_y)] = best_sc
    return mapping


# ---------------------------------------------------------------------------
# 4. 应用映射：把「源模式三元组」翻译成「统一本体三元组」
# ---------------------------------------------------------------------------

# 一条实例事实：(头实体文本, 关系名, 尾实体文本, 头类型, 尾类型)
RawTriple = Tuple[str, str, str, str, str]


def translate_triples(
    raw_triples: List[RawTriple],
    mapping: SchemaMapping,
) -> List[dict]:
    """
    ETL 核心一步：按 SchemaMapping 改写类型名与关系名。

    输入（源系统 A 抽出来的）：
      ("贵州茅台", "listedCode", "600519", "Corp", "Ticker")

    输出（对齐到本项目本体后）：
      {"head":"贵州茅台", "relation":"LISTED_AS",
       "tail":"600519", "head_type":"Company", "tail_type":"Stock"}

    注意：这里只改「模式标签」；「贵州茅台」本身是实例，留给实体对齐处理。
    """
    out: List[dict] = []
    for head, rel, tail, h_type, t_type in raw_triples:
        out.append(
            {
                "head": head,  # 实例名先原样保留
                "tail": tail,
                "relation": mapping.relation_map.get(rel, rel),  # listedCode → LISTED_AS
                "head_type": mapping.class_map.get(h_type, h_type),  # Corp → Company
                "tail_type": mapping.class_map.get(t_type, t_type),  # Ticker → Stock
                "source_relation": rel,  # 溯源：原来叫什么
                "source_head_type": h_type,
                "source_tail_type": t_type,
            }
        )
    return out


def demo_contrast_with_entity_alignment() -> None:
    """打印对照表，避免和「茅台/Moutai」搞混。"""
    print("\n【概念对照】不要和实体对齐搞混")
    print("  模式对齐：Corp ──≡──→ Company      （改的是『词性/类名』）")
    print("  实体对齐：茅台 ──≡──→ 贵州茅台    （改的是『指谁』）")
    print("  正确顺序：先模式对齐，再实体对齐，最后入库。")


def demo() -> None:
    print("=" * 60)
    print("本体/模式对齐：匹配 → 映射表 → 翻译三元组")
    print("=" * 60)

    demo_contrast_with_entity_alignment()

    # ----- 两个异构模式 -----
    source_a = Schema(
        name="行情系统A（外源）",
        classes=["Corp", "Ticker", "Sector"],
        relations=["listedCode", "控股"],
        attributes=["证券代码", "corpName"],
    )
    target = Schema(
        name="本项目统一本体",
        classes=["Company", "Stock", "Industry"],
        relations=["LISTED_AS", "CONTROLS"],
        attributes=["code", "name"],
    )

    # ----- 步骤1：算出映射表 -----
    print(f"\n【1] 模式匹配】{source_a.name} → {target.name}")
    mapping = match_schemas(source_a, target, threshold=0.5)
    print("  类映射:")
    for s, t in mapping.class_map.items():
        sc = mapping.scores.get(("class", s, t), 0)
        print(f"    {s:12s}  ≡  {t:12s}  score={sc:.2f}")
    print("  关系映射:")
    for s, t in mapping.relation_map.items():
        sc = mapping.scores.get(("relation", s, t), 0)
        print(f"    {s:12s}  ≡  {t:12s}  score={sc:.2f}")
    print("  属性映射:")
    for s, t in mapping.attribute_map.items():
        sc = mapping.scores.get(("attribute", s, t), 0)
        print(f"    {s:12s}  ≡  {t:12s}  score={sc:.2f}")

    # ----- 步骤2：外源抽到的「脏」三元组（仍用 A 的类名/关系名）-----
    raw_from_a: List[RawTriple] = [
        # (头, 关系, 尾, 头类型, 尾类型) —— 全是系统 A 的词
        ("贵州茅台", "listedCode", "600519", "Corp", "Ticker"),
        ("茅台集团", "控股", "贵州茅台", "Corp", "Corp"),
        ("贵州茅台", "listedCode", "600519", "Corp", "Ticker"),  # 故意重复，看翻译后仍同构
    ]
    print("\n【2] 外源原始三元组】（模式尚未对齐）")
    for h, r, t, ht, tt in raw_from_a:
        print(f"  ({h}:{ht}) -[{r}]-> ({t}:{tt})")

    # ----- 步骤3：应用映射，变成统一本体语言 -----
    unified = translate_triples(raw_from_a, mapping)
    print("\n【3] 翻译后（已对齐到本项目本体）】")
    for row in unified:
        print(
            f"  ({row['head']}:{row['head_type']}) "
            f"-[{row['relation']}]-> "
            f"({row['tail']}:{row['tail_type']})  "
            f"← 原 {row['source_head_type']}/[{row['source_relation']}]/{row['source_tail_type']}"
        )

    print("\n【4] 之后做什么】")
    print("  → 实体对齐：把「茅台」「Moutai」并到「贵州茅台」（实例层）")
    print("  → MERGE 进 Neo4j：标签用 Company/Stock，边用 LISTED_AS/CONTROLS")
    print("\n速记：模式对齐改『词典』；实体对齐改『指称』；二者都要，顺序是模式→实例。")


if __name__ == "__main__":
    demo()
