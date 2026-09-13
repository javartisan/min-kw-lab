#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
学习小点：Embedding（嵌入表示）
一句话：把实体/关系映射到向量空间，用距离做相似度与补全。

对应笔记：docs/1-知识表示.html → Embedding
说明：这里用手写 toy 向量演示直觉，不引入 PyTorch。
"""

from __future__ import annotations

import math
from typing import Dict, List, Tuple


Vec = List[float]


def dot(a: Vec, b: Vec) -> float:
    return sum(x * y for x, y in zip(a, b))


def norm(a: Vec) -> float:
    return math.sqrt(sum(x * x for x in a))


def cosine(a: Vec, b: Vec) -> float:
    """余弦相似度：1 表示同向，0 正交，-1 反向。"""
    denom = norm(a) * norm(b)
    return 0.0 if denom == 0 else dot(a, b) / denom


def add(a: Vec, b: Vec) -> Vec:
    return [x + y for x, y in zip(a, b)]


def sub(a: Vec, b: Vec) -> Vec:
    return [x - y for x, y in zip(a, b)]


# ---------------------------------------------------------------------------
# 手工构造的「伪嵌入」：维度含义仅供直觉
#   dim0: 白酒属性   dim1: 新能源   dim2: 是否上市公司
# ---------------------------------------------------------------------------

ENTITY_EMB: Dict[str, Vec] = {
    "贵州茅台": [0.95, 0.05, 1.0],
    "五粮液": [0.90, 0.08, 1.0],
    "宁德时代": [0.05, 0.95, 1.0],
    "白酒": [1.00, 0.00, 0.0],  # 行业不是公司，第三维可不同
    "动力电池": [0.00, 1.00, 0.0],
}

# TransE 直觉： head + relation ≈ tail
# 这里手工给一个 BELONGS_TO 关系向量
REL_EMB: Dict[str, Vec] = {
    "BELONGS_TO": [-0.05, 0.0, -1.0],  # 公司→行业：削弱「上市」维，保留行业方向
}


def most_similar(query: str, candidates: List[str], k: int = 3) -> List[Tuple[str, float]]:
    q = ENTITY_EMB[query]
    scored = [(c, cosine(q, ENTITY_EMB[c])) for c in candidates if c != query]
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:k]


def transe_score(head: str, rel: str, tail: str) -> float:
    """
    TransE 打分：|| h + r - t || 越小越好。
    教学用：用负的 L2 距离当分数，越大越像「成立」。
    """
    h, r, t = ENTITY_EMB[head], REL_EMB[rel], ENTITY_EMB[tail]
    diff = sub(add(h, r), t)
    dist = math.sqrt(sum(x * x for x in diff))
    return -dist


def demo() -> None:
    print("=" * 60)
    print("Embedding 学习脚本：相似度 + TransE 直觉")
    print("=" * 60)

    print("\n【实体向量（手工）】")
    for name, v in ENTITY_EMB.items():
        print(f"  {name:8s}  {v}")

    print("\n【谁和「贵州茅台」最像？】")
    for name, score in most_similar("贵州茅台", list(ENTITY_EMB)):
        print(f"  {name:8s}  cosine={score:.3f}")

    print("\n【TransE：贵州茅台 + BELONGS_TO ≈ ?】")
    for industry in ("白酒", "动力电池"):
        s = transe_score("贵州茅台", "BELONGS_TO", industry)
        print(f"  → {industry:8s}  score={s:.3f}  (越大越像真三元组)")

    print(
        "\n三者关系：Ontology 定语义 → RDF/OWL 落形式 → Embedding 做计算增强（可并存）。"
    )
    print("速记：符号表示擅长精确约束；向量表示擅长模糊相似与补全。")


if __name__ == "__main__":
    demo()
