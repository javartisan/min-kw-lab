#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
学习小点：Embedding（嵌入表示）
一句话：把实体/关系映射到向量空间，用距离做相似度与补全。

对应笔记：docs/1-知识表示.html → Embedding
说明：这里用手写 toy 向量演示直觉，不引入 PyTorch。
真实工程可用 TransE / RotatE / ComplEx 等模型训练得到向量。
"""

from __future__ import annotations

import math
from typing import Dict, List, Tuple


# 向量别名：一串浮点数，如 [0.95, 0.05, 1.0]
Vec = List[float]


def dot(a: Vec, b: Vec) -> float:
    """
    【点积 / 内积】逐维相乘再求和。

    公式：a·b = Σ a_i * b_i

    用途：
      是余弦相似度、很多神经网络打分的基础运算。

    参数：
      a, b — 等长向量

    返回：
      标量；同向且大时结果偏大，反向时偏小/为负

    例子：
      dot([1, 0], [1, 0]) → 1.0
      dot([1, 0], [0, 1]) → 0.0
    """
    return sum(x * y for x, y in zip(a, b))


def norm(a: Vec) -> float:
    """
    【L2 范数 / 欧氏长度】向量的「长度」。

    公式：||a|| = sqrt(Σ a_i²)

    用途：
      余弦相似度要除以两边长度；TransE 也用 L2 距离。

    参数：
      a — 向量

    返回：
      非负浮点数；零向量返回 0.0
    """
    return math.sqrt(sum(x * x for x in a))


def cosine(a: Vec, b: Vec) -> float:
    """
    【余弦相似度】只看方向是否接近，不看绝对长度。

    公式：cos(a,b) = (a·b) / (||a|| * ||b||)

    取值直觉：
      1  — 完全同向（最相似）
      0  — 正交（无关）
     -1  — 完全反向

    参数：
      a, b — 两个实体（或任意）向量

    返回：
      [-1, 1] 上的相似度；若任一方为零向量则返回 0.0 避免除零

    KG 用法：
      找「和贵州茅台最像的公司」→ 对候选算 cosine，取 Top-K
    """
    denom = norm(a) * norm(b)
    return 0.0 if denom == 0 else dot(a, b) / denom


def add(a: Vec, b: Vec) -> Vec:
    """
    【向量加法】逐维相加，得到新向量。

    在 TransE 中：head + relation 表示「头实体沿关系平移后的位置」。

    参数：
      a, b — 等长向量

    返回：
      新列表，不修改入参

    例子：
      add([1, 2], [0.1, -1]) → [1.1, 1.0]
    """
    return [x + y for x, y in zip(a, b)]


def sub(a: Vec, b: Vec) -> Vec:
    """
    【向量减法】逐维相减。

    在 TransE 打分中：
      (h + r) - t  的长度越小，说明「头+关系」越接近尾，三元组越可信。

    参数：
      a, b — 等长向量

    返回：
      新列表 a - b
    """
    return [x - y for x, y in zip(a, b)]


# ---------------------------------------------------------------------------
# 手工构造的「伪嵌入」：维度含义仅供直觉（不是训练出来的）
#   dim0: 白酒相关程度
#   dim1: 新能源相关程度
#   dim2: 是否偏「上市公司」语义（行业可为 0）
# ---------------------------------------------------------------------------

ENTITY_EMB: Dict[str, Vec] = {
    "贵州茅台": [0.95, 0.05, 1.0],
    "五粮液": [0.90, 0.08, 1.0],
    "宁德时代": [0.05, 0.95, 1.0],
    "白酒": [1.00, 0.00, 0.0],
    "动力电池": [0.00, 1.00, 0.0],
}

# TransE 直觉： head + relation ≈ tail
# BELONGS_TO：公司→行业时，削弱「上市」维（dim2），保留行业方向
REL_EMB: Dict[str, Vec] = {
    "BELONGS_TO": [-0.05, 0.0, -1.0],
}


def most_similar(
    query: str,
    candidates: List[str],
    k: int = 3,
) -> List[Tuple[str, float]]:
    """
    【近邻检索】找出与 query 实体余弦相似度最高的 k 个候选。

    步骤：
      1. 取出 query 的向量
      2. 对每个候选（排除自己）算 cosine
      3. 按分数降序排序，取前 k 个

    参数：
      query      — 查询实体名，必须已在 ENTITY_EMB 中
      candidates — 候选实体名列表
      k          — 返回条数，默认 3

    返回：
      [(实体名, 相似度), ...]，相似度从高到低

    工程对照：
      真实系统会用 FAISS / Annoy 做百万级近似近邻；这里是精确暴力扫描。
    """
    q = ENTITY_EMB[query]
    scored = [(c, cosine(q, ENTITY_EMB[c])) for c in candidates if c != query]
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:k]


def transe_score(head: str, rel: str, tail: str) -> float:
    """
    【TransE 打分】衡量三元组 (head, rel, tail) 有多「像真的」。

    TransE 假设：
      向量空间里  h + r ≈ t
      即：头实体加上关系平移后，应落在尾实体附近

    本函数：
      计算 ||(h + r) - t|| 的 L2 距离，再取负号作为分数
      → 距离越小，分数越大，越像成立的三元组

    参数：
      head — 头实体名，如 "贵州茅台"
      rel  — 关系名，如 "BELONGS_TO"（须在 REL_EMB）
      tail — 尾实体名，如 "白酒"

    返回：
      浮点分数（越大越好）；仅用于相对比较，绝对值无物理单位

    例子：
      transe_score("贵州茅台", "BELONGS_TO", "白酒")
        应高于
      transe_score("贵州茅台", "BELONGS_TO", "动力电池")
    """
    h, r, t = ENTITY_EMB[head], REL_EMB[rel], ENTITY_EMB[tail]
    diff = sub(add(h, r), t)  # (h + r) - t
    dist = math.sqrt(sum(x * x for x in diff))  # L2 距离
    return -dist


def demo() -> None:
    """
    演示入口：打印玩具向量 → 相似公司 → TransE 链接预测直觉。

    对照笔记三句话：
      Ontology 定语义 → RDF/OWL 落形式 → Embedding 做计算增强（可并存）
    """
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
