#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
学习小点：实体对齐（Entity Alignment）
一句话：识别「多个提及是否指向同一现实对象」，再软链或硬合并。

对应笔记：docs/5-知识融合.html → 实体对齐
口诀：先硬键（代码），再名字，最后向量；合并前保留来源。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class Record:
    id: str
    source: str
    name: str
    code: Optional[str] = None
    aliases: List[str] = field(default_factory=list)


def normalize_name(name: str) -> str:
    """名称归一：去公司后缀、空白。"""
    s = name.strip().lower()
    for suf in ("股份有限公司", "有限公司", "集团", "co.,ltd.", "co., ltd."):
        s = s.replace(suf, "")
    return "".join(s.split())


def name_similarity(a: str, b: str) -> float:
    """简易字符 Jaccard；生产可用编辑距离/拼音/Embedding。"""
    sa, sb = set(normalize_name(a)), set(normalize_name(b))
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


# 中英别名桥接（实务中来自别名词表）
CANONICAL_ALIAS = {
    "kweichowmoutai": "贵州茅台",
    "贵州茅台": "贵州茅台",
    "茅台": "贵州茅台",
    "五粮液": "五粮液",
}


def all_names(r: Record) -> set:
    raw = {r.name, *r.aliases}
    norms = {normalize_name(x) for x in raw}
    # 映射到规范中文名后再比较
    canon = {CANONICAL_ALIAS.get(n, n) for n in norms}
    return norms | canon


def align_score(a: Record, b: Record) -> Tuple[float, str]:
    """
    对齐信号由强到弱：
      代码相同 → 1.0
      名称/别名命中 → 高分
      字符串相似 → 中分
    """
    if a.code and b.code and a.code == b.code:
        return 1.0, "code"
    if all_names(a) & all_names(b):
        return 0.95, "alias"
    sim = name_similarity(a.name, b.name)
    if sim >= 0.55:
        return sim, "string"
    return 0.0, "none"


def cluster(records: List[Record], threshold: float = 0.8) -> List[List[Record]]:
    """贪心聚类：与簇内任一成员分数够高则并入（便于代码簇再吸名称记录）。"""
    clusters: List[List[Record]] = []
    for r in records:
        placed = False
        for c in clusters:
            if any(align_score(r, m)[0] >= threshold for m in c):
                c.append(r)
                placed = True
                break
        if not placed:
            clusters.append([r])
    return clusters


def demo() -> None:
    print("=" * 60)
    print("实体对齐学习脚本：硬键 / 别名 / 相似度")
    print("=" * 60)

    records = [
        Record("a1", "研报", "贵州茅台", code=None, aliases=["茅台"]),
        # 英文名通过别名词表桥接到「贵州茅台」；再与行情代码对齐
        Record(
            "a2",
            "英文公告",
            "Kweichow Moutai Co.,Ltd.",
            code="600519",
            aliases=["Kweichow Moutai", "贵州茅台"],
        ),
        Record("a3", "行情", "600519.SH 发行人", code="600519"),
        Record("b1", "新闻", "五粮液", code="000858"),
    ]

    print("\n【两两打分】")
    for i in range(len(records)):
        for j in range(i + 1, len(records)):
            sc, why = align_score(records[i], records[j])
            print(
                f"  {records[i].id} vs {records[j].id}: "
                f"{sc:.2f} ({why})  | {records[i].name[:12]} ~ {records[j].name[:20]}"
            )

    print("\n【聚类结果】（可 SAME_AS 软对齐或 MERGE 硬合并）")
    for i, c in enumerate(cluster(records), 1):
        print(f"  簇{i}: {[r.id + ':' + r.source for r in c]}")

    print("\n速记：同名异实要靠代码/信用代码消歧；粒度不同（集团 vs 股份）勿盲目合并。")


if __name__ == "__main__":
    demo()
