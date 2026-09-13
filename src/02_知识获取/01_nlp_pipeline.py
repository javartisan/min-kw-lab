#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
学习小点：NLP 抽取流水线（总览）
一句话：文档进 → 预处理 → NER → RE/EE → 对齐本体 → 子图出。

对应笔记：docs/2-知识获取.html → NLP 抽取
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Tuple


@dataclass
class Entity:
    text: str
    type: str  # 对齐本体后的类型：Company / Stock / Industry ...
    start: int
    end: int


@dataclass
class Triple:
    head: str
    relation: str
    tail: str
    confidence: float = 1.0


@dataclass
class ExtractedGraph:
    """抽取结果：可入库的迷你子图。"""

    entities: List[Entity] = field(default_factory=list)
    triples: List[Triple] = field(default_factory=list)


def extract_text_from_pseudo_doc(raw: str) -> str:
    """文档解析的教学替代：去掉页眉页脚噪声。"""
    lines = []
    for line in raw.splitlines():
        s = line.strip()
        if not s or s.startswith("页眉:") or s.startswith("---"):
            continue
        lines.append(s)
    return " ".join(lines)


def preprocess(text: str) -> List[str]:
    """预处理：按句号分句（极简）。"""
    parts = [p.strip() for p in text.replace("！", "。").split("。")]
    return [p for p in parts if p]


def rule_ner(sentence: str) -> List[Entity]:
    """规则/词典 NER（仓库笔记中的冷启动路线）。"""
    lexicon = {
        "贵州茅台": "Company",
        "白酒": "Industry",
        "600519": "Stock",
    }
    found: List[Entity] = []
    for name, typ in lexicon.items():
        idx = sentence.find(name)
        if idx >= 0:
            found.append(Entity(name, typ, idx, idx + len(name)))
    found.sort(key=lambda e: e.start)
    return found


def rule_re(sentence: str, entities: List[Entity]) -> List[Triple]:
    """模板关系抽取：看见「属于…行业」就连 BELONGS_TO。"""
    triples: List[Triple] = []
    names = {e.type: e.text for e in entities}
    if "属于" in sentence and "行业" in sentence:
        if "Company" in names and "Industry" in names:
            triples.append(Triple(names["Company"], "BELONGS_TO", names["Industry"], 0.9))
    if "股票代码" in sentence or "代码是" in sentence:
        if "Company" in names and "Stock" in names:
            triples.append(Triple(names["Company"], "LISTED_AS", names["Stock"], 0.95))
    return triples


def align_to_ontology(graph: ExtractedGraph) -> ExtractedGraph:
    """后处理：类型已是本体名；这里演示去重。"""
    uniq_e = {(e.text, e.type): e for e in graph.entities}
    uniq_t = {(t.head, t.relation, t.tail): t for t in graph.triples}
    return ExtractedGraph(list(uniq_e.values()), list(uniq_t.values()))


def run_pipeline(raw_doc: str) -> ExtractedGraph:
    """端到端：读文 → 抽知识。"""
    text = extract_text_from_pseudo_doc(raw_doc)
    graph = ExtractedGraph()
    for sent in preprocess(text):
        ents = rule_ner(sent)
        graph.entities.extend(ents)
        graph.triples.extend(rule_re(sent, ents))
    return align_to_ontology(graph)


def demo() -> None:
    print("=" * 60)
    print("NLP 抽取流水线：文档进、子图出")
    print("=" * 60)

    raw = """
页眉: 证券研究报告
---
贵州茅台属于白酒行业。贵州茅台的股票代码是600519。
"""
    print("\n【原文】")
    print(raw.strip())

    g = run_pipeline(raw)
    print("\n【实体】")
    for e in g.entities:
        print(f"  [{e.text}] {e.type}")

    print("\n【三元组】（可 MERGE 进 Neo4j）")
    for t in g.triples:
        print(f"  ({t.head}) -[{t.relation} conf={t.confidence}]-> ({t.tail})")

    print("\n速记：表示规定「能有哪些类与边」；获取负责「从文本把实例填进去」。")


if __name__ == "__main__":
    demo()
