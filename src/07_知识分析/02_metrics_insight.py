#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
学习小点：指标洞察（Metrics / OLAP on KG）
一句话：把业务问题定义成可计算指标，在图谱上聚合与监控。

对应笔记：docs/7-知识分析.html → 指标洞察
"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Dict, List, Tuple


# 模拟 getStats / 聚合查询的结果源
ENTITIES = [
    ("贵州茅台", "Company"),
    ("五粮液", "Company"),
    ("宁德时代", "Company"),
    ("600519", "Stock"),
    ("000858", "Stock"),
    ("300750", "Stock"),
    ("白酒", "Industry"),
    ("动力电池", "Industry"),
    ("丁雄军", "Person"),
    ("研报A", "Document"),
]

RELS = [
    ("贵州茅台", "LISTED_AS", "600519"),
    ("五粮液", "LISTED_AS", "000858"),
    ("宁德时代", "LISTED_AS", "300750"),
    ("贵州茅台", "BELONGS_TO", "白酒"),
    ("五粮液", "BELONGS_TO", "白酒"),
    ("宁德时代", "BELONGS_TO", "动力电池"),
    ("贵州茅台", "HAS_EXECUTIVE", "丁雄军"),
    ("研报A", "MENTIONS", "贵州茅台"),
    ("研报A", "MENTIONS", "白酒"),
]


def stats_overview() -> Dict:
    by_type = Counter(t for _, t in ENTITIES)
    return {
        "entities": len(ENTITIES),
        "relations": len(RELS),
        "byType": dict(by_type),
    }


def industry_coverage() -> List[Tuple[str, int]]:
    """各行业下公司数。"""
    c = Counter(o for s, p, o in RELS if p == "BELONGS_TO")
    return c.most_common()


def relation_histogram() -> List[Tuple[str, int]]:
    return Counter(p for _, p, _ in RELS).most_common()


def quality_gaps() -> Dict[str, List[str]]:
    """
    图谱完整度/质量缺口：
      - 有公司无行业
      - 有公司无股票代码
    """
    companies = {n for n, t in ENTITIES if t == "Company"}
    has_industry = {s for s, p, _ in RELS if p == "BELONGS_TO"}
    has_stock = {s for s, p, _ in RELS if p == "LISTED_AS"}
    return {
        "缺行业": sorted(companies - has_industry),
        "缺代码": sorted(companies - has_stock),
    }


def avg_degree() -> float:
    deg = defaultdict(int)
    for s, _, o in RELS:
        deg[s] += 1
        deg[o] += 1
    if not deg:
        return 0.0
    return sum(deg.values()) / len(deg)


def demo() -> None:
    print("=" * 60)
    print("指标洞察学习脚本：规模 / 分布 / 质量")
    print("=" * 60)

    print("\n【总览 getStats】")
    print(" ", stats_overview())

    print("\n【行业覆盖】")
    for ind, n in industry_coverage():
        print(f"  {ind}: {n} 家公司")

    print("\n【关系类型直方图】")
    for rel, n in relation_histogram():
        print(f"  {rel}: {n}")

    print(f"\n【平均度数】{avg_degree():.2f}")

    print("\n【质量缺口】")
    for k, v in quality_gaps().items():
        print(f"  {k}: {v or '无'}")

    print("\n互补：行情/财务进数仓；关系/事件进图谱；分析层可 JOIN。")


if __name__ == "__main__":
    demo()
