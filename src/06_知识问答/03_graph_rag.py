#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
学习小点：GraphRAG
一句话：先检索相关子图/路径作上下文，再生成自然语言答复。

对应笔记：docs/6-知识问答.html → GraphRAG
对比 KBQA：KBQA 直接返结构化答案；GraphRAG 用证据生成可读叙述。
"""

from __future__ import annotations

from typing import Dict, List, Set, Tuple


Triple = Tuple[str, str, str]

# 更大一点的证据库
GRAPH: List[Triple] = [
    ("贵州茅台", "BELONGS_TO", "白酒"),
    ("贵州茅台", "LISTED_AS", "600519"),
    ("贵州茅台", "HAS_EXECUTIVE", "丁雄军"),
    ("贵州茅台", "COMPETES_WITH", "五粮液"),
    ("五粮液", "BELONGS_TO", "白酒"),
    ("茅台集团", "CONTROLS", "贵州茅台"),
    ("丁雄军", "TITLE", "董事长"),
]


def retrieve_subgraph(seed_entities: List[str], hops: int = 1) -> List[Triple]:
    """
    子图检索：从种子实体出发，取 k 跳内三元组。
    生产可用：向量召回实体 + Cypher 扩边 / Personalized PageRank。
    """
    frontier: Set[str] = set(seed_entities)
    collected: List[Triple] = []
    seen: Set[Triple] = set()

    for _ in range(hops):
        nxt: Set[str] = set()
        for s, p, o in GRAPH:
            if s in frontier or o in frontier:
                t = (s, p, o)
                if t not in seen:
                    seen.add(t)
                    collected.append(t)
                    nxt.add(s)
                    nxt.add(o)
        frontier |= nxt
    return collected


def triples_to_context(triples: List[Triple]) -> str:
    """把子图序列化成给「生成器」的上下文。"""
    lines = [f"- ({s}) -[{p}]-> ({o})" for s, p, o in triples]
    return "已知图谱证据:\n" + "\n".join(lines)


def generate_answer(question: str, context: str) -> str:
    """
    教学替身：不调用真实 LLM，按模板把证据拼成自然语言。
    真实 GraphRAG：context + question → LLM → 答复，并要求引用证据。
    """
    bullets: List[str] = []
    if "行业" in question and "BELONGS_TO" in context:
        bullets.append("行业：贵州茅台 —BELONGS_TO→ 白酒")
    if ("董事长" in question or "谁" in question) and "HAS_EXECUTIVE" in context:
        bullets.append("高管：贵州茅台 —HAS_EXECUTIVE→ 丁雄军")
    if "竞争" in question and "COMPETES_WITH" in context:
        bullets.append("竞争：贵州茅台 —COMPETES_WITH→ 五粮液")
    if ("控制" in question or "控股" in question) and "CONTROLS" in context:
        bullets.append("控股：茅台集团 —CONTROLS→ 贵州茅台")
    if not bullets:
        return "已检索到相关子图，但规则生成器无法覆盖该问法。可接入 LLM 并强制引用证据。"
    return "基于检索子图的答复：\n- " + "\n- ".join(bullets) + "\n（未出现在证据中的事实不应编造）"


def demo() -> None:
    print("=" * 60)
    print("GraphRAG 学习脚本：检索子图 → 生成答复")
    print("=" * 60)

    question = "贵州茅台的董事长是谁？和谁竞争？属于什么行业？"
    seeds = ["贵州茅台"]
    sub = retrieve_subgraph(seeds, hops=1)
    ctx = triples_to_context(sub)

    print(f"\n【问题】{question}")
    print(f"\n【检索子图】({len(sub)} 条)")
    print(ctx)

    print("\n【生成答复】")
    print(generate_answer(question, ctx))

    print("\n要点：没有检索到的边，生成器不该「脑补」；证券场景尤其要防幻觉。")


if __name__ == "__main__":
    demo()
