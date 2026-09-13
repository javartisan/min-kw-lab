#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
学习小点：RDF 存储
一句话：用三元组库存语义数据，用 SPARQL 查询，可挂 OWL 推理。

对应笔记：docs/3-知识存储.html → RDF
代表：Jena TDB / GraphDB / Virtuoso；本脚本用内存三元组模拟。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple


Triple = Tuple[str, str, str]


@dataclass
class TripleStore:
    """迷你 RDF 三元组库。"""

    triples: Set[Triple] = field(default_factory=set)

    def insert(self, s: str, p: str, o: str) -> None:
        self.triples.add((s, p, o))

    def load_turtle_like(self, lines: List[str]) -> None:
        """极简解析：每行 `s p o`（空格分隔，教学用）。"""
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            s, p, o = line.split(None, 2)
            self.insert(s, p, o)

    def sparql_select_where(
        self, patterns: List[Triple]
    ) -> List[Dict[str, str]]:
        """
        极简 BGP（Basic Graph Pattern）匹配。
        变量以 ? 开头，如 (?s, rdf:type, Company)
        """
        solutions: List[Dict[str, str]] = [{}]

        def is_var(x: str) -> bool:
            return x.startswith("?")

        for ps, pp, po in patterns:
            nxt: List[Dict[str, str]] = []
            for sol in solutions:
                for s, p, o in self.triples:
                    cand = dict(sol)
                    ok = True
                    for term, val in ((ps, s), (pp, p), (po, o)):
                        if is_var(term):
                            if term in cand and cand[term] != val:
                                ok = False
                                break
                            cand[term] = val
                        elif term != val:
                            ok = False
                            break
                    if ok:
                        nxt.append(cand)
            solutions = nxt
        return solutions


def demo() -> None:
    print("=" * 60)
    print("RDF 存储学习脚本：三元组入库 + 迷你 SPARQL")
    print("=" * 60)

    store = TripleStore()
    # 与 docs/examples/securities-mini.ttl 同构的事实
    store.load_turtle_like(
        [
            "Moutai rdf:type ListedCompany",
            "Moutai listedAs S600519",
            "Moutai rdfs:label 贵州茅台",
            "S600519 rdf:type Stock",
            "ListedCompany rdfs:subClassOf Company",
            "白酒 rdf:type Industry",
            "Moutai belongsTo 白酒",
        ]
    )

    print(f"\n【库中三元组数】{len(store.triples)}")

    # SELECT ?company ?industry WHERE {
    #   ?company belongsTo ?industry .
    #   ?company rdf:type ListedCompany .
    # }
    print("\n【SPARQL 直觉】谁属于哪个行业？")
    rows = store.sparql_select_where(
        [
            ("?company", "belongsTo", "?industry"),
            ("?company", "rdf:type", "ListedCompany"),
        ]
    )
    for r in rows:
        print(f"  company={r['?company']}  industry={r['?industry']}")

    print("\n【属性图 vs RDF】")
    print("  属性图：节点/边可挂任意属性，业务查询友好（Neo4j）")
    print("  RDF：统一三元组 + IRI，互操作与 OWL 推理友好")
    print("  实务可并存：业务库用 Neo4j，交换/推理用 RDF 导出")


if __name__ == "__main__":
    demo()
