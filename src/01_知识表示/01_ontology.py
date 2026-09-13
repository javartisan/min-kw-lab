#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
学习小点：Ontology（本体）
一句话：本体 = 领域里「共享概念体系」的形式化约定。

对应笔记：docs/1-知识表示.html → Ontology、TBox/ABox
核心问题：这个领域里，词是什么意思、能不能连、有什么限制？

分层直觉：
  TBox（模式层）= 类 / 属性 / 公理
  ABox（数据层）= 个体与具体事实
  知识库 KB ≈ TBox + ABox
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# 1. 本体的四个构件：类 / 个体 / 属性 / 公理
# ---------------------------------------------------------------------------

@dataclass
class OntologyClass:
    """类（Concept）：事物的类别，如 Company、Stock。"""

    name: str
    parent: Optional[str] = None  # 父类名；None 表示顶层类


@dataclass
class Individual:
    """个体（Instance）：类的具体实例，如「贵州茅台」。"""

    name: str
    class_name: str
    data_props: dict[str, str] = field(default_factory=dict)  # 数据属性：实体→字面量


@dataclass
class ObjectProperty:
    """对象属性：实体 → 实体 的关系，如 LISTED_AS。"""

    name: str
    domain: str  # 定义域：起点必须属于的类
    range: str  # 值域：终点必须属于的类
    min_card_on_range: int = 0  # 对 range 侧的最小基数（简化公理）


@dataclass
class Ontology:
    """一个极简「证券本体」容器。"""

    classes: dict[str, OntologyClass] = field(default_factory=dict)
    properties: dict[str, ObjectProperty] = field(default_factory=dict)
    individuals: dict[str, Individual] = field(default_factory=dict)
    facts: list[tuple[str, str, str]] = field(default_factory=list)  # (s, p, o)

    def add_class(self, name: str, parent: Optional[str] = None) -> None:
        self.classes[name] = OntologyClass(name, parent)

    def is_subclass_of(self, child: str, ancestor: str) -> bool:
        """沿父类链向上走，判断 child 是否属于 ancestor 体系。"""
        cur: Optional[str] = child
        while cur is not None:
            if cur == ancestor:
                return True
            parent = self.classes[cur].parent if cur in self.classes else None
            cur = parent
        return False

    def assert_fact(self, subject: str, predicate: str, obj: str) -> None:
        """写入一条关系事实，并做轻量约束检查（教学用）。"""
        if subject not in self.individuals:
            raise ValueError(f"未知个体: {subject}")
        if obj not in self.individuals:
            raise ValueError(f"未知个体: {obj}")
        if predicate not in self.properties:
            raise ValueError(f"未知关系: {predicate}")

        prop = self.properties[predicate]
        subj = self.individuals[subject]
        obj_ind = self.individuals[obj]

        # 定义域 / 值域：起点、终点的类型要符合本体约定
        if not self.is_subclass_of(subj.class_name, prop.domain):
            raise TypeError(
                f"{subject} 类型 {subj.class_name} 不满足 {predicate} 的定义域 {prop.domain}"
            )
        if not self.is_subclass_of(obj_ind.class_name, prop.range):
            raise TypeError(
                f"{obj} 类型 {obj_ind.class_name} 不满足 {predicate} 的值域 {prop.range}"
            )

        self.facts.append((subject, predicate, obj))


def build_securities_ontology() -> Ontology:
    """
    证券最小本体片段（笔记中的三行）：

      类：Company ⊇ ListedCompany
      关系：ListedCompany —LISTED_AS→ Stock
      约束：一只 Stock 至少对应一家 ListedCompany
    """
    onto = Ontology()

    # 类层次：ListedCompany 是 Company 的子类
    onto.add_class("Company")
    onto.add_class("ListedCompany", parent="Company")
    onto.add_class("Stock")

    # 对象属性 + 基数约束（这里用 min_card_on_range 表达「Stock 侧至少 1」）
    onto.properties["LISTED_AS"] = ObjectProperty(
        name="LISTED_AS",
        domain="ListedCompany",
        range="Stock",
        min_card_on_range=1,
    )

    # 个体
    onto.individuals["贵州茅台"] = Individual("贵州茅台", "ListedCompany")
    onto.individuals["600519"] = Individual(
        "600519", "Stock", data_props={"code": "600519"}
    )

    # 事实：贵州茅台 —LISTED_AS→ 600519
    onto.assert_fact("贵州茅台", "LISTED_AS", "600519")
    return onto


def check_cardinality(onto: Ontology) -> list[str]:
    """检查「每只 Stock 至少有一条指向它的 LISTED_AS」。"""
    problems: list[str] = []
    prop = onto.properties["LISTED_AS"]
    stocks = [i for i in onto.individuals.values() if i.class_name == "Stock"]
    for stock in stocks:
        incoming = [f for f in onto.facts if f[1] == "LISTED_AS" and f[2] == stock.name]
        if len(incoming) < prop.min_card_on_range:
            problems.append(f"孤儿股票: {stock.name} 缺少 LISTED_AS 入边")
    return problems


def demo() -> None:
    print("=" * 60)
    print("Ontology 学习脚本：证券最小本体")
    print("=" * 60)

    onto = build_securities_ontology()

    print("\n【类层次】")
    for name, cls in onto.classes.items():
        parent = cls.parent or "(顶层)"
        print(f"  {name}  ⊆  {parent}" if cls.parent else f"  {name}  (顶层)")

    print("\n【关系】")
    for p in onto.properties.values():
        print(f"  {p.domain} —{p.name}→ {p.range}  (Stock侧最少{p.min_card_on_range}条)")

    print("\n【事实】")
    for s, p, o in onto.facts:
        print(f"  {s} —{p}→ {o}")

    # 子类推理直觉：ListedCompany 的实例也是 Company
    moutai = onto.individuals["贵州茅台"]
    print("\n【子类直觉】")
    print(f"  贵州茅台 显式类型: {moutai.class_name}")
    print(f"  是否也是 Company? {onto.is_subclass_of(moutai.class_name, 'Company')}")

    print("\n【基数约束检查】")
    problems = check_cardinality(onto)
    print("  通过" if not problems else "\n".join(f"  ! {p}" for p in problems))

    # 反例：普通 Company 不能 LISTED_AS（定义域不满足）
    print("\n【约束失败演示】")
    onto.individuals["某非上市合伙企业"] = Individual("某非上市合伙企业", "Company")
    onto.individuals["999999"] = Individual("999999", "Stock")
    try:
        onto.assert_fact("某非上市合伙企业", "LISTED_AS", "999999")
    except TypeError as e:
        print(f"  预期报错: {e}")

    print(
        "\n速记：先本体后落库 —— 先定 Company/Stock/LISTED_AS，再映射到 Neo4j 标签与边。"
    )


if __name__ == "__main__":
    demo()
