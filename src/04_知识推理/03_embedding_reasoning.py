#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
学习小点：Embedding 推理（链接预测）
一句话：在向量空间里对「缺失三元组」打分，做知识补全。

对应笔记：docs/4-知识推理.html → Embedding
与表示层 Embedding 的关系：同一套向量，这里侧重「推理/补全」用法。
"""

from __future__ import annotations

import math
from typing import Dict, List, Tuple


Vec = List[float]
Triple = Tuple[str, str, str]


def l2(a: Vec) -> float:
    return math.sqrt(sum(x * x for x in a))


def add(a: Vec, b: Vec) -> Vec:
    return [x + y for x, y in zip(a, b)]


def sub(a: Vec, b: Vec) -> Vec:
    return [x - y for x, y in zip(a, b)]


# 已知训练三元组（显式知识）
TRAIN: List[Triple] = [
    ("贵州茅台", "BELONGS_TO", "白酒"),
    ("五粮液", "BELONGS_TO", "白酒"),
    ("宁德时代", "BELONGS_TO", "动力电池"),
    ("贵州茅台", "LISTED_AS", "600519"),
]

# 手工 toy 嵌入（真实应用由 TransE/RotatE/ComplEx 训练得到）
E: Dict[str, Vec] = {
    "贵州茅台": [1.0, 0.1, 1.0],
    "五粮液": [0.95, 0.12, 1.0],
    "宁德时代": [0.1, 1.0, 1.0],
    "白酒": [1.0, 0.1, 0.0],
    "动力电池": [0.1, 1.0, 0.0],
    "600519": [1.0, 0.1, 0.5],
    "300750": [0.1, 1.0, 0.5],
}
R: Dict[str, Vec] = {
    "BELONGS_TO": [0.0, 0.0, -1.0],
    "LISTED_AS": [0.0, 0.0, -0.5],
}


def score(h: str, r: str, t: str) -> float:
    """TransE：||h+r-t|| 越小越好 → 返回负距离。"""
    d = sub(add(E[h], R[r]), E[t])
    return -l2(d)


def predict_tail(head: str, rel: str, candidates: List[str], k: int = 3) -> List[Tuple[str, float]]:
    """链接预测：固定头实体与关系，对候选尾实体排序。"""
    ranked = [(c, score(head, rel, c)) for c in candidates]
    ranked.sort(key=lambda x: x[1], reverse=True)
    return ranked[:k]


def demo() -> None:
    print("=" * 60)
    print("Embedding 推理：链接预测补全")
    print("=" * 60)

    print("\n【已知三元组】")
    for t in TRAIN:
        print(f"  {t}")

    # 假设库里缺了「五粮液 LISTED_AS ?」
    print("\n【预测】五粮液 —LISTED_AS→ ?")
    for name, sc in predict_tail("五粮液", "LISTED_AS", ["600519", "300750", "白酒"]):
        print(f"  {name:8s}  score={sc:.3f}")

    print("\n【预测】宁德时代 —BELONGS_TO→ ?")
    for name, sc in predict_tail(
        "宁德时代", "BELONGS_TO", ["白酒", "动力电池", "600519"]
    ):
        print(f"  {name:8s}  score={sc:.3f}")

    print("\n三类推理组合：规则可解释、本体可校验、Embedding 能补洞。")
    print("速记：向量推理是概率候选，入库前要阈值或人工审核。")


if __name__ == "__main__":
    demo()
