#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
学习小点：RDF / OWL
一句话：RDF 用三元组写事实；OWL 在其上加公理，让机器能推理。

对应笔记：docs/1-知识表示.html → RDF/OWL、TBox/ABox
对照文件：docs/examples/securities-mini.ttl

TBox（模式层）= 类 / 属性 / 公理；ABox（数据层）= 个体与断言。
推理 ≈ 用 TBox 规矩去补全或校验 ABox 事实。
"""

from __future__ import annotations

from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# RDF：一切皆三元组 (Subject, Predicate, Object)
# ---------------------------------------------------------------------------

Triple = tuple[str, str, str]  # 教学简化：用短名代替完整 IRI


@dataclass
class RdfGraph:
    """内存里的迷你 RDF 图。"""

    triples: list[Triple] = field(default_factory=list)

    def add(self, s: str, p: str, o: str) -> None:
        self.triples.append((s, p, o))

    def ask(self, s: str | None = None, p: str | None = None, o: str | None = None) -> list[Triple]:
        """按模式匹配查询（None 表示通配）。"""
        out: list[Triple] = []
        for t in self.triples:
            if s is not None and t[0] != s:
                continue
            if p is not None and t[1] != p:
                continue
            if o is not None and t[2] != o:
                continue
            out.append(t)
        return out


def load_securities_facts() -> RdfGraph:
    """
    对应 Turtle 中的显式断言（省略前缀，便于阅读）：

      :Moutai a :ListedCompany
      :Moutai :listedAs :S600519
      :S600519 a :Stock
      :ListedCompany rdfs:subClassOf :Company
      :Person owl:disjointWith :Company
    """
    g = RdfGraph()
    # 模式层（TBox）：类层次、属性定义、互斥公理
    g.add("ListedCompany", "rdfs:subClassOf", "Company")
    g.add("Person", "owl:disjointWith", "Company")
    g.add("listedAs", "rdfs:domain", "ListedCompany")
    g.add("listedAs", "rdfs:range", "Stock")
    # 数据层（ABox）：具体个体与断言
    g.add("Moutai", "rdf:type", "ListedCompany")
    g.add("Moutai", "listedAs", "S600519")
    g.add("S600519", "rdf:type", "Stock")
    g.add("Moutai", "rdfs:label", "贵州茅台")
    return g


# ---------------------------------------------------------------------------
# 极简 RDFS 推理：子类传递 → 实例也属于父类
# ---------------------------------------------------------------------------

def rdfs_type_closure(g: RdfGraph) -> list[Triple]:
    """
    规则：
      IF  (?x rdf:type ?C) AND (?C rdfs:subClassOf ?D)
      THEN (?x rdf:type ?D)
    可迭代到不动点（这里类层次很浅，跑几轮即可）。
    """
    inferred: list[Triple] = []
    known = set(g.triples)

    changed = True
    while changed:
        changed = False
        type_facts = [(s, o) for s, p, o in known if p == "rdf:type"]
        subclass = [(s, o) for s, p, o in known if p == "rdfs:subClassOf"]
        for x, c in type_facts:
            for child, parent in subclass:
                if c == child:
                    neo = (x, "rdf:type", parent)
                    if neo not in known:
                        known.add(neo)
                        inferred.append(neo)
                        changed = True
    return inferred


def check_disjoint(g: RdfGraph, inferred: list[Triple]) -> list[str]:
    """若某个体同时是互斥两类的实例 → 不一致。"""
    all_triples = set(g.triples) | set(inferred)
    types: dict[str, set[str]] = {}
    for s, p, o in all_triples:
        if p == "rdf:type":
            types.setdefault(s, set()).add(o)

    disjoint_pairs = [(s, o) for s, p, o in all_triples if p == "owl:disjointWith"]
    # 互斥通常对称，补全另一方向
    pairs = set(disjoint_pairs) | {(b, a) for a, b in disjoint_pairs}

    conflicts: list[str] = []
    for entity, tset in types.items():
        for a, b in pairs:
            if a in tset and b in tset:
                conflicts.append(f"{entity} 同时是 {a} 与 {b} → 不一致")
    return conflicts


def demo() -> None:
    print("=" * 60)
    print("RDF/OWL 学习脚本：三元组 + 子类推理 + 互斥校验")
    print("=" * 60)

    g = load_securities_facts()
    print("\n【显式三元组】")
    for t in g.triples:
        print(f"  {t[0]}  —{t[1]}→  {t[2]}")

    inferred = rdfs_type_closure(g)
    print("\n【RDFS 推出】（未写入、由公理得到）")
    for t in inferred:
        print(f"  {t[0]}  —{t[1]}→  {t[2]}   # Moutai 因 ListedCompany⊆Company")

    print("\n【一致性】当前应无冲突")
    print(" ", check_disjoint(g, inferred) or "OK")

    # 故意制造冲突：再断言茅台是 Person
    print("\n【冲突演示】再断言 Moutai rdf:type Person")
    g.add("Moutai", "rdf:type", "Person")
    inferred2 = rdfs_type_closure(g)
    print(" ", check_disjoint(g, inferred2))

    print(
        "\n速记：Ontology 定语义 → RDF 落三元组 → OWL 公理交给推理器；"
        "完整 Turtle 见 docs/examples/securities-mini.ttl"
    )


if __name__ == "__main__":
    demo()
