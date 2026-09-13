#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
学习小点：RDF / OWL
一句话：RDF 用三元组写事实；OWL 在其上加公理，让机器能推理。

对应笔记：docs/1-知识表示.html → RDF/OWL、Turtle（TTL）、TBox/ABox
对照文件：docs/examples/securities-mini.ttl

要点：
  - TTL 不是编程语言，是 RDF 的文本序列化（Turtle）
  - TBox（模式层）= 类 / 属性 / 公理；ABox（数据层）= 个体与断言
  - 推理 ≈ 用 TBox 规矩去补全或校验 ABox 事实
"""

from __future__ import annotations

from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# RDF：一切皆三元组 (Subject, Predicate, Object)
# ---------------------------------------------------------------------------

# 教学简化：用短名字符串代替完整 IRI
# 真实工程里应是 http://example.org/sec#Moutai 这类全球唯一标识
Triple = tuple[str, str, str]


@dataclass
class RdfGraph:
    """
    【迷你 RDF 图】内存中的三元组集合。

    真实系统对应：Jena Model / RDF4J Repository / Neo4j 里导出的 RDF 等。
    本类只保留「存三元组 + 按模式查询」两个核心动作，方便理解 RDF 模型。

    字段：
      triples — [(主语, 谓语, 宾语), ...]，顺序即插入顺序
    """

    triples: list[Triple] = field(default_factory=list)

    def add(self, s: str, p: str, o: str) -> None:
        """
        追加一条三元组（断言一条事实或一条公理）。

        参数：
          s — Subject  主语（资源短名），如 "Moutai"
          p — Predicate 谓语（属性/关系），如 "rdf:type"、"listedAs"
          o — Object   宾语（资源或字面量），如 "ListedCompany"、"贵州茅台"

        说明：
          - 这里不做去重；同一条可被 add 多次（教学上更直观）
          - Turtle 里的 `a` 就是 `rdf:type` 的缩写

        例子：
          g.add("Moutai", "rdf:type", "ListedCompany")
          # 读作：Moutai 的类型是 ListedCompany
        """
        self.triples.append((s, p, o))

    def ask(
        self,
        s: str | None = None,
        p: str | None = None,
        o: str | None = None,
    ) -> list[Triple]:
        """
        按「模式匹配」查询三元组（SPARQL 最简 BGP 的直觉版）。

        规则：
          参数为 None 表示该位置通配（任意值都匹配）；
          参数非 None 则必须与三元组对应位完全相等。

        参数：
          s / p / o — 可选的精确匹配条件

        返回：
          所有命中的三元组列表（可能为空）

        例子：
          g.ask(s="Moutai")                 → 茅台相关的所有边
          g.ask(p="rdf:type")               → 所有类型断言
          g.ask(s="Moutai", p="rdf:type")   → 茅台的类型有哪些
        """
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
    加载与 docs/examples/securities-mini.ttl 同构的显式三元组。

    分为两层（务必分清）：
      TBox（模式）：子类、互斥、属性 domain/range
      ABox（数据）：Moutai 是上市公司、listedAs 某股票 等

    返回：
      已填好显式断言的 RdfGraph（尚未跑推理）

    Turtle 对照（节选）：
      :ListedCompany rdfs:subClassOf :Company .
      :Moutai a :ListedCompany ; :listedAs :S600519 .
    """
    g = RdfGraph()

    # ----- TBox：术语 / 模式 -----
    g.add("ListedCompany", "rdfs:subClassOf", "Company")  # 子类公理
    g.add("Person", "owl:disjointWith", "Company")  # 互斥公理
    g.add("listedAs", "rdfs:domain", "ListedCompany")  # 属性定义域
    g.add("listedAs", "rdfs:range", "Stock")  # 属性值域

    # ----- ABox：断言 / 实例 -----
    g.add("Moutai", "rdf:type", "ListedCompany")
    g.add("Moutai", "listedAs", "S600519")
    g.add("S600519", "rdf:type", "Stock")
    g.add("Moutai", "rdfs:label", "贵州茅台")  # 人类可读标签（字面量）
    return g


def rdfs_type_closure(g: RdfGraph) -> list[Triple]:
    """
    【RDFS 类型闭包】根据子类公理，推出实例对父类的 rdf:type。

    核心规则（可反复应用直到不动点）：
      IF   (?x  rdf:type         ?C)
       AND (?C  rdfs:subClassOf  ?D)
      THEN (?x  rdf:type         ?D)

    证券例子：
      显式：Moutai rdf:type ListedCompany
      公理：ListedCompany rdfs:subClassOf Company
      推出：Moutai rdf:type Company   ← 你没手写，推理得到

    参数：
      g — 含显式三元组的 RDF 图

    返回：
      新推出的三元组列表（不含原本就在 g.triples 里的）

    注意：
      真实工程用 HermiT/Pellet/ELK；这里用手写循环演示「推理在干什么」。
    """
    inferred: list[Triple] = []
    known = set(g.triples)  # 用 set 便于 O(1) 判断「是否已有」

    changed = True
    while changed:
        changed = False
        # 拆出当前所有类型断言与子类公理
        type_facts = [(s, o) for s, p, o in known if p == "rdf:type"]
        subclass = [(s, o) for s, p, o in known if p == "rdfs:subClassOf"]
        for x, c in type_facts:
            for child, parent in subclass:
                if c == child:
                    neo = (x, "rdf:type", parent)
                    if neo not in known:
                        known.add(neo)
                        inferred.append(neo)
                        changed = True  # 有新增，可能触发下一轮传递
    return inferred


def check_disjoint(g: RdfGraph, inferred: list[Triple]) -> list[str]:
    """
    【一致性检查】若个体同时属于一对互斥类 → 报告冲突。

    依据公理：
      Person owl:disjointWith Company
      含义：任何个体不能既是 Person 又是 Company（含经推理得到的类型）

    参数：
      g        — 显式三元组图
      inferred — rdfs_type_closure 等推出的额外类型

    返回：
      冲突描述字符串列表；空列表表示当前一致

    例子：
      正常：Moutai 只有 ListedCompany/Company → []
      冲突：再断言 Moutai rdf:type Person → ["Moutai 同时是 ..."]
    """
    # 显式 + 推出 = 推理器眼中的完整 ABox 类型视图
    all_triples = set(g.triples) | set(inferred)

    # 收集每个实体的全部类型
    types: dict[str, set[str]] = {}
    for s, p, o in all_triples:
        if p == "rdf:type":
            types.setdefault(s, set()).add(o)

    # 取出互斥对，并补成对称（A⊥B ⇔ B⊥A）
    disjoint_pairs = [(s, o) for s, p, o in all_triples if p == "owl:disjointWith"]
    pairs = set(disjoint_pairs) | {(b, a) for a, b in disjoint_pairs}

    conflicts: list[str] = []
    for entity, tset in types.items():
        for a, b in pairs:
            if a in tset and b in tset:
                conflicts.append(f"{entity} 同时是 {a} 与 {b} → 不一致")
    return conflicts


def demo() -> None:
    """
    演示入口：显式三元组 → 子类推理补全 → 一致性 OK → 故意制造冲突。

    对照学习：
      1. load_securities_facts  = 读 .ttl 里「写死」的内容
      2. rdfs_type_closure     = Protégé 里 Inferred 多出来的类型
      3. check_disjoint        = 推理器报 inconsistent
    """
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

    # 故意制造冲突：再断言茅台是 Person（与 Company 互斥）
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
