#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
学习小点：冲突消解（Conflict Resolution）
一句话：多源说法打架时，按策略取舍，并保留溯源与置信度。

对应笔记：docs/5-知识融合.html → 冲突消解
常见策略：权威源优先 / 多数投票 / 时间最新 / 置信度加权 / 人工裁决。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class Claim:
    """一条带出处的断言：某实体的某属性 = 某值。"""

    subject: str
    attr: str
    value: Any
    source: str
    confidence: float
    as_of: date


# 源权威等级（教学示例）
SOURCE_RANK = {
    "交易所公告": 100,
    "公司年报": 90,
    "券商研报": 60,
    "新闻媒体": 40,
    "论坛传闻": 10,
}


def resolve_authority(claims: List[Claim]) -> Claim:
    """权威源优先；同分再比日期与置信度。"""
    return max(
        claims,
        key=lambda c: (SOURCE_RANK.get(c.source, 0), c.as_of, c.confidence),
    )


def resolve_vote(claims: List[Claim]) -> Tuple[Any, Dict[Any, float]]:
    """加权投票：同一值累加 confidence。"""
    scores: Dict[Any, float] = {}
    for c in claims:
        scores[c.value] = scores.get(c.value, 0.0) + c.confidence
    winner = max(scores, key=scores.get)
    return winner, scores


def resolve_latest(claims: List[Claim]) -> Claim:
    """时间最新优先（适合会变的事实，如董事长）。"""
    return max(claims, key=lambda c: c.as_of)


def demo() -> None:
    print("=" * 60)
    print("冲突消解学习脚本：多策略仲裁")
    print("=" * 60)

    subject = "贵州茅台"
    # 冲突1：董事长姓名不一致
    chair_claims = [
        Claim(subject, "董事长", "张三", "新闻媒体", 0.7, date(2023, 1, 5)),
        Claim(subject, "董事长", "丁雄军", "交易所公告", 0.99, date(2024, 6, 1)),
        Claim(subject, "董事长", "丁雄军", "公司年报", 0.95, date(2024, 3, 30)),
    ]

    # 冲突2：持股比例数值不同
    ratio_claims = [
        Claim(subject, "第一大股东持股比", 0.54, "公司年报", 0.95, date(2024, 3, 30)),
        Claim(subject, "第一大股东持股比", 0.52, "券商研报", 0.80, date(2024, 8, 1)),
        Claim(subject, "第一大股东持股比", 0.54, "交易所公告", 0.99, date(2024, 3, 30)),
    ]

    print("\n【董事长】权威源策略")
    best = resolve_authority(chair_claims)
    print(f"  采纳: {best.value}  来自 {best.source} @ {best.as_of}")

    print("\n【董事长】最新时间策略")
    best = resolve_latest(chair_claims)
    print(f"  采纳: {best.value}  @ {best.as_of}")

    print("\n【持股比】加权投票")
    winner, scores = resolve_vote(ratio_claims)
    print(f"  票分: {scores}")
    print(f"  采纳: {winner}")

    print("\n【写入图谱时建议保留】")
    print("  value + source + confidence + as_of")
    print("  不要只留最终值——融合要可追溯，冲突才可审计。")


if __name__ == "__main__":
    demo()
