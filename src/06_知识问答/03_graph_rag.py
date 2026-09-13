#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
学习小点：GraphRAG（子图检索来自 Neo4j）
一句话：先检索相关子图作上下文，再生成自然语言答复。

对应笔记：docs/6-知识问答.html → GraphRAG
工程：检索用 Cypher/路径；生成侧可接 LLM，但必须引用检索到的边。
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from common.neo4j_client import get_lab_tag, require_neo4j, run_cypher
from common.seed_kg import ensure_seed_graph

Triple = Tuple[str, str, str]


def retrieve_subgraph(seed: str, hops: int = 1) -> List[Triple]:
    """从种子实体取 1 跳出边/入边（可扩展为变长路径或向量召回+扩边）。"""
    lab = get_lab_tag()
    if hops != 1:
        # 教学先做 1 跳；多跳可用 [:REL*1..n]
        hops = 1
    rows = run_cypher(
        """
        MATCH (s {name: $name, lab: $lab})-[r]-(n {lab: $lab})
        RETURN s.name AS s, type(r) AS p, n.name AS o,
               startNode(r).name AS start, endNode(r).name AS end
        """,
        {"name": seed, "lab": lab},
    )
    triples: List[Triple] = []
    seen = set()
    for row in rows:
        t = (row["start"], row["p"], row["end"])
        if t not in seen:
            seen.add(t)
            triples.append(t)
    return triples


def triples_to_context(triples: List[Triple]) -> str:
    lines = [f"- ({s}) -[{p}]-> ({o})" for s, p, o in triples]
    return "已知图谱证据:\n" + "\n".join(lines)


def generate_answer(question: str, context: str) -> str:
    """教学替身：规则拼装；生产换 LLM，并强制「无证据不答」。"""
    bullets: List[str] = []
    if "行业" in question and "BELONGS_TO" in context:
        bullets.append("行业：证据中存在 BELONGS_TO")
    if ("董事长" in question or "谁" in question) and "HAS_EXECUTIVE" in context:
        bullets.append("高管：证据中存在 HAS_EXECUTIVE")
    if "竞争" in question and "COMPETES_WITH" in context:
        bullets.append("竞争：证据中存在 COMPETES_WITH")
    if not bullets:
        return "已检索子图，但生成器未覆盖该问法；可接入 LLM 并强制引用下列证据。\n" + context
    return "基于 Neo4j 检索子图的答复：\n- " + "\n- ".join(bullets) + "\n\n" + context


def demo() -> None:
    print("=" * 60)
    print("GraphRAG：Neo4j 检索子图 → 生成答复")
    print("=" * 60)

    question = "贵州茅台的董事长是谁？和谁竞争？属于什么行业？"
    with require_neo4j():
        ensure_seed_graph(reset=False)
        sub = retrieve_subgraph("贵州茅台", hops=1)
        ctx = triples_to_context(sub)
        print(f"\n【问题】{question}")
        print(f"\n【检索】{len(sub)} 条")
        print(ctx)
        print("\n【答复】")
        print(generate_answer(question, ctx))


if __name__ == "__main__":
    demo()
