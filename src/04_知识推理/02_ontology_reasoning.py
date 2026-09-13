#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
学习小点：本体推理（Ontology-based Reasoning）
一句话：依据 RDFS/OWL 公理做分类补全与一致性检查。

对应笔记：docs/4-知识推理.html → 本体推理
对照：docs/examples/securities-mini.ttl
"""

from __future__ import annotations

from typing import Dict, List, Set, Tuple


Triple = Tuple[str, str, str]


class MiniOwlReasoner:
    """
    教学向推理器，覆盖笔记中的两类能力：
      1) 补全：子类实例 ⇒ 父类实例
      2) 一致性：互斥类不能同时成立
    真实工程用 HermiT / Pellet / ELK。
    """

    def __init__(self, triples: List[Triple]) -> None:
        self.explicit = set(triples)
        self.inferred: Set[Triple] = set()

    @property
    def all(self) -> Set[Triple]:
        return self.explicit | self.inferred

    def subclass_pairs(self) -> List[Tuple[str, str]]:
        return [(s, o) for s, p, o in self.all if p == "rdfs:subClassOf"]

    def types_of(self, x: str) -> Set[str]:
        return {o for s, p, o in self.all if s == x and p == "rdf:type"}

    def classify(self) -> None:
        """分类学推理：沿 subClassOf 向上关闭。"""
        changed = True
        while changed:
            changed = False
            for x, c in [(s, o) for s, p, o in self.all if p == "rdf:type"]:
                for child, parent in self.subclass_pairs():
                    if c == child:
                        neo = (x, "rdf:type", parent)
                        if neo not in self.all:
                            self.inferred.add(neo)
                            changed = True

    def consistency(self) -> List[str]:
        """互斥检查。"""
        disjoint = [(s, o) for s, p, o in self.all if p == "owl:disjointWith"]
        pairs = set(disjoint) | {(b, a) for a, b in disjoint}
        problems = []
        entities = {s for s, p, _ in self.all if p == "rdf:type"}
        for e in entities:
            t = self.types_of(e)
            for a, b in pairs:
                if a in t and b in t:
                    problems.append(f"不一致: {e} 既是 {a} 又是 {b}")
        return problems


def demo() -> None:
    print("=" * 60)
    print("本体推理学习脚本：补全 + 一致性")
    print("=" * 60)

    tbox_abox = [
        ("ListedCompany", "rdfs:subClassOf", "Company"),
        ("Person", "owl:disjointWith", "Company"),
        ("Moutai", "rdf:type", "ListedCompany"),
        ("Moutai", "listedAs", "S600519"),
        ("S600519", "rdf:type", "Stock"),
    ]

    r = MiniOwlReasoner(tbox_abox)
    r.classify()

    print("\n【显式】Moutai rdf:type ListedCompany")
    print("【推出】")
    for t in sorted(r.inferred):
        print(f"  {t}")

    print("\n【一致性】", r.consistency() or "OK")

    print("\n【再断言 Moutai rdf:type Person】")
    r.explicit.add(("Moutai", "rdf:type", "Person"))
    r.classify()
    print(" ", r.consistency())

    print("\n对比规则推理：规则偏业务 IF-THEN；本体偏描述逻辑公理。")
    print("速记：补全少写多得；一致性帮你抓脏数据。")


if __name__ == "__main__":
    demo()
