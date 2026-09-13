#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
学习小点：NLP 抽取流水线（总览）
一句话：文档进 → 预处理 → NER → RE/EE → 对齐本体 → 子图出。

对应笔记：docs/2-知识获取.html → NLP 抽取
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
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
    # 含中英别名，便于演示后续 align 时合并为「贵州茅台」
    lexicon = {
        "贵州茅台": "Company",
        "茅台": "Company",
        "Moutai": "Company",
        "白酒": "Industry",
        "600519": "Stock",
    }
    found: List[Entity] = []
    # 长词优先，避免「贵州茅台」被拆成更短的「茅台」
    for name, typ in sorted(lexicon.items(), key=lambda kv: len(kv[0]), reverse=True):
        idx = sentence.find(name)
        if idx < 0:
            continue
        # 与已占用区间重叠则跳过（最长匹配）
        if any(e.start <= idx < e.end or e.start < idx + len(name) <= e.end for e in found):
            continue
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


# 规范实体名（别名词表）：多提及 → 同一现实对象的标准名
# 实务中常来自工商别名库 / 行情代码桥接 / 人工审核表
ENTITY_CANONICAL = {
    "茅台": "贵州茅台",
    "moutai": "贵州茅台",
    "kweichow moutai": "贵州茅台",
    "kweichow moutai co.,ltd.": "贵州茅台",
    "贵州茅台": "贵州茅台",
    "贵州茅台酒股份有限公司": "贵州茅台",
}


def canonicalize_entity_name(name: str) -> str:
    """
    实体对齐（实例层）的最简一步：别名 → 规范名。

    例子：
      "茅台" / "Moutai" / "Kweichow Moutai" → "贵州茅台"

    注意：这与「本体对齐/模式匹配」不同——
      本体对齐解决 Company ≡ Corp（概念同义）；
      实体对齐解决 茅台 ≡ Moutai（对象同指）。
    """
    key = name.strip().lower()
    # 先精确查表（小写键）；查不到再试去空格的英文变体
    if key in ENTITY_CANONICAL:
        return ENTITY_CANONICAL[key]
    compact = "".join(key.split())
    for alias, canon in ENTITY_CANONICAL.items():
        if "".join(alias.split()) == compact:
            return canon
    return name  # 词表没有则保持原文，留给更强对齐（代码/向量）


def align_to_ontology(graph: ExtractedGraph) -> ExtractedGraph:
    """
    后处理：抽取结果 → 可入库子图。

    本教学版包含两层「对齐」直觉：

      A. 实体对齐（实例同指）
         茅台 / Moutai → 统一成规范名「贵州茅台」
         （词表不够时，工程上再用股票代码、向量近邻等，见
          src/05_知识融合/01_entity_alignment.py）

      B. 去重
         同一 (规范名, 类型) 实体只留一条；
         同一 (头, 关系, 尾) 三元组只留一条

      C. 类型已对齐本体（本脚本 NER 直接产出 Company/Stock…）
         若上游产出 Corp/Ticker，这里还应做模式映射（本体匹配）
    """
    # A. 实体对齐：把别名改写成规范名（含三元组里头尾）
    normalized_entities: List[Entity] = []
    for e in graph.entities:
        canon = canonicalize_entity_name(e.text)
        # 保留原 span；入库主键用规范名
        normalized_entities.append(Entity(canon, e.type, e.start, e.end))

    normalized_triples: List[Triple] = []
    for t in graph.triples:
        normalized_triples.append(
            Triple(
                canonicalize_entity_name(t.head),
                t.relation,
                canonicalize_entity_name(t.tail),
                t.confidence,
            )
        )

    # B. 去重：规范名相同的「茅台」与「Moutai」此时已合成同一键
    uniq_e = {(e.text, e.type): e for e in normalized_entities}
    uniq_t = {(t.head, t.relation, t.tail): t for t in normalized_triples}
    return ExtractedGraph(list(uniq_e.values()), list(uniq_t.values()))


def run_pipeline(raw_doc: str) -> ExtractedGraph:
    """
    端到端流水线框架（文档进 → 子图出）：

      ① 文档解析  extract_text_from_pseudo_doc
      ② 预处理    preprocess（分句）
      ③ NER       rule_ner（找实体：NER = Named Entity Recognition）
      ④ RE        rule_re（连关系：RE = Relation Extraction）
      ⑤ 本体对齐  align_to_ontology（去重/规范化）
    """
    # ① 文档解析：去掉页眉/分隔线等噪声，得到可处理的纯文本
    text = extract_text_from_pseudo_doc(raw_doc)
    # 准备空结果容器：后续各句抽出的实体与三元组都往这里累积
    graph = ExtractedGraph()
    # ② 预处理：把纯文本按句号切成句子列表，逐句进入抽取阶段
    for sent in preprocess(text):
        # ③ NER：在当前句子里定位实体边界并打上本体类型（Company/Stock/…）
        ents = rule_ner(sent)
        # 把本句识别到的实体追加进总图（多句会多次 extend）
        graph.entities.extend(ents)
        # ④ RE：基于本句文本 + 已识别实体，抽关系三元组并追加进总图
        graph.triples.extend(rule_re(sent, ents))
    # ⑤ 后处理/本体对齐：实体与三元组去重，类型已对齐本体名后返回可入库子图
    return align_to_ontology(graph)


def demo() -> None:
    print("=" * 60)
    print("NLP 抽取流水线：文档进、子图出")
    print("=" * 60)

    raw = """
页眉: 证券研究报告
---
贵州茅台属于白酒行业。Moutai的股票代码是600519。茅台又称酱香龙头。
"""
    print("\n【原文】")
    print(raw.strip())

    g = run_pipeline(raw)
    print("\n【实体】（茅台/Moutai 应对齐成「贵州茅台」）")
    for e in g.entities:
        print(f"  [{e.text}] {e.type}")

    print("\n【三元组】（可 MERGE 进 Neo4j）")
    for t in g.triples:
        print(f"  ({t.head}) -[{t.relation} conf={t.confidence}]-> ({t.tail})")

    # 工程可选：python 01_nlp_pipeline.py --neo4j
    if "--neo4j" in sys.argv:
        ingest_to_neo4j(g)

    print("\n速记：表示规定「能有哪些类与边」；获取负责「从文本把实例填进去」。")
    print("落库演示：python src/02_知识获取/01_nlp_pipeline.py --neo4j")


def ingest_to_neo4j(graph: ExtractedGraph) -> None:
    """抽取结果 MERGE 进 Neo4j（真实入库链路）。"""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from common.neo4j_client import get_lab_tag, require_neo4j, run_cypher

    label_map = {
        "Company": "Company",
        "Stock": "Stock",
        "Industry": "Industry",
        "Person": "Person",
    }
    with require_neo4j():
        lab = get_lab_tag()
        print("\n【入库 Neo4j】")
        for e in graph.entities:
            label = label_map.get(e.type, "Entity")
            run_cypher(
                f"""
                MERGE (n:{label} {{name: $name, lab: $lab}})
                SET n.entityType = $typ, n.source = 'nlp_pipeline'
                """,
                {"name": e.text, "lab": lab, "typ": e.type},
                write=True,
            )
            print(f"  MERGE (:{label} {{name:{e.text!r}}})")
        for t in graph.triples:
            run_cypher(
                f"""
                MATCH (a {{name: $h, lab: $lab}})
                MATCH (b {{name: $t, lab: $lab}})
                MERGE (a)-[r:{t.relation} {{lab: $lab}}]->(b)
                SET r.confidence = $conf, r.source = 'nlp_pipeline'
                """,
                {
                    "h": t.head,
                    "t": t.tail,
                    "lab": lab,
                    "conf": t.confidence,
                },
                write=True,
            )
            print(f"  MERGE ({t.head})-[:{t.relation}]->({t.tail})")


if __name__ == "__main__":
    demo()
