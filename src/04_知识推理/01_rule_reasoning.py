#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
学习小点：规则推理（内存引擎 + Neo4j Cypher 物化）
一句话：IF 条件模式成立 THEN 断言新事实 / 告警。

对应笔记：docs/4-知识推理.html → 规则推理
工程实践：小规则可写在应用层；图上模式匹配常用 Cypher MERGE 物化推断边。
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Set, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from common.neo4j_client import get_lab_tag, require_neo4j, run_cypher
from common.seed_kg import ensure_seed_graph

Fact = Tuple[str, str, str]


@dataclass
class RuleEngine:
    """教学用内存前向链（对照 Cypher 规则）。"""

    facts: Set[Fact] = field(default_factory=set)
    inferred: List[Fact] = field(default_factory=list)
    alerts: List[str] = field(default_factory=list)

    def assert_fact(self, s: str, p: str, o: str, inferred: bool = False) -> None:
        f = (s, p, o)
        if f in self.facts:
            return
        self.facts.add(f)
        if inferred:
            self.inferred.append(f)

    def match(self, s=None, p=None, o=None) -> List[Fact]:
        out = []
        for a, b, c in self.facts:
            if s is not None and a != s:
                continue
            if p is not None and b != p:
                continue
            if o is not None and c != o:
                continue
            out.append((a, b, c))
        return out

    def run(self) -> None:
        for a, _, b in self.match(p="CONTROLS"):
            for _, _, c in self.match(s=b, p="CONTROLS"):
                self.assert_fact(a, "CONTROLS_INDIRECT", c, inferred=True)
        for x, _, _ in self.match(p="LISTED_AS"):
            self.assert_fact(x, "rdf:type", "ListedCompany", inferred=True)
        people = {s for s, p, _ in self.facts if p == "HAS_EXECUTIVE_OF"}
        for person in people:
            cos = [o for _, _, o in self.match(s=person, p="HAS_EXECUTIVE_OF")]
            for i in range(len(cos)):
                for j in range(i + 1, len(cos)):
                    c1, c2 = cos[i], cos[j]
                    if (c1, "COMPETES_WITH", c2) in self.facts or (
                        c2,
                        "COMPETES_WITH",
                        c1,
                    ) in self.facts:
                        self.alerts.append(
                            f"同高管关联竞品: {person} 任职于 {c1} 与 {c2}"
                        )


def neo4j_materialize_rules() -> None:
    """
    真实工程写法：用 Cypher 表达规则并 MERGE 推断边。
    注意：只物化高频、有解释需求的规则；传递闭包别无脑全展开。
    """
    lab = get_lab_tag()

    print("\n【Neo4j R1】间接控股 → CONTROLS_INDIRECT {inferred:true}")
    rows = run_cypher(
        """
        MATCH (a:Company {lab: $lab})-[:CONTROLS]->(:Company {lab: $lab})
              -[:CONTROLS]->(c:Company {lab: $lab})
        MERGE (a)-[r:CONTROLS_INDIRECT {lab: $lab}]->(c)
        SET r.inferred = true, r.depth = 2, r.rule = 'R1'
        RETURN a.name AS a, c.name AS c
        """,
        {"lab": lab},
        write=True,
    )
    for row in rows:
        print(f"  {row['a']} -[:CONTROLS_INDIRECT]-> {row['c']}")

    print("\n【Neo4j R2】有 LISTED_AS → 打 ListedCompany 标签")
    rows = run_cypher(
        """
        MATCH (x:Company {lab: $lab})-[:LISTED_AS]->(:Stock {lab: $lab})
        SET x:ListedCompany
        SET x.inferredListed = true
        RETURN x.name AS name
        """,
        {"lab": lab},
        write=True,
    )
    for row in rows:
        print(f"  {row['name']} +:ListedCompany")

    print("\n【Neo4j R3】风控查询（同人任职竞品）— 本种子数据无同人双职，演示查询形态")
    alerts = run_cypher(
        """
        MATCH (p:Person {lab: $lab})<-[:HAS_EXECUTIVE]-(c1:Company {lab: $lab})
        MATCH (p)<-[:HAS_EXECUTIVE]-(c2:Company {lab: $lab})
        WHERE id(c1) < id(c2)
          AND EXISTS { MATCH (c1)-[:COMPETES_WITH]-(c2) }
        RETURN p.name AS person, c1.name AS c1, c2.name AS c2
        """,
        {"lab": lab},
    )
    if not alerts:
        print("  （当前种子无命中；可手工加「同一人任职两家竞品」再跑）")
    for row in alerts:
        print(f"  ! {row['person']} @ {row['c1']} & {row['c2']}")


def demo() -> None:
    print("=" * 60)
    print("规则推理：内存 IF-THEN + Neo4j Cypher 物化")
    print("=" * 60)

    eng = RuleEngine()
    eng.assert_fact("茅台集团", "CONTROLS", "贵州茅台")
    eng.assert_fact("贵州茅台", "CONTROLS", "某销售子公司")
    eng.assert_fact("贵州茅台", "LISTED_AS", "600519")
    eng.assert_fact("丁某", "HAS_EXECUTIVE_OF", "贵州茅台")
    eng.assert_fact("丁某", "HAS_EXECUTIVE_OF", "五粮液")
    eng.assert_fact("贵州茅台", "COMPETES_WITH", "五粮液")
    eng.run()

    print("\n【内存推出】")
    for f in eng.inferred:
        print(f"  {f}")
    print("【内存告警】")
    for a in eng.alerts:
        print(f"  ! {a}")

    with require_neo4j():
        ensure_seed_graph(reset=False)
        neo4j_materialize_rules()

    print("\n速记：规则要可解释；图上物化用 MERGE + inferred 标记，便于审计与回滚。")


if __name__ == "__main__":
    demo()
