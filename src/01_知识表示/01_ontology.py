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

import json
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# 1. 本体的四个构件：类 / 个体 / 属性 / 公理
# ---------------------------------------------------------------------------

@dataclass
class OntologyClass:
    """
    【类 / Concept】事物的类别（TBox 的一部分）。

    作用：
      告诉机器「世界上有哪几种东西」，并可用 parent 表达 is-a 层级。

    字段：
      name   — 类名，如 "Company"、"Stock"
      parent — 父类名；None 表示顶层类（没有更上的父类）

    例子：
      OntologyClass("ListedCompany", parent="Company")
      读作：ListedCompany ⊆ Company（上市公司是公司的一种）
    """

    name: str
    parent: Optional[str] = None  # 父类名；None = 顶层类


@dataclass
class Individual:
    """
    【个体 / Instance】类的具体成员（ABox 的一部分）。

    作用：
      把抽象的类落到真实世界对象上，成为图谱里的「实体节点」。

    字段：
      name       — 个体标识，如 "贵州茅台"
      class_name — 显式所属类，如 "ListedCompany"
      data_props — 数据属性（实体→字面量），如 {"code": "600519"}
                   注意：这不是对象属性；对象属性在 Ontology.facts 里

    例子：
      Individual("贵州茅台", "ListedCompany")
      Individual("600519", "Stock", data_props={"code": "600519"})
    """

    name: str
    class_name: str
    data_props: dict[str, str] = field(default_factory=dict)


@dataclass
class ObjectProperty:
    """
    【对象属性】连接「实体 → 实体」的关系谓词（TBox）。

    和数据属性的差别：
      - 对象属性：两端都是个体，如 贵州茅台 —LISTED_AS→ 600519
      - 数据属性：一端个体、一端字面量，如 code="600519"
        （本脚本数据属性挂在 Individual.data_props，不单独建类）

    证券举例 — LISTED_AS（上市为）：
      domain = ListedCompany   # 谁可以当起点
      range  = Stock           # 谁可以当终点
      合法：贵州茅台(ListedCompany) —LISTED_AS→ 600519(Stock)
      非法：白酒(Industry) —LISTED_AS→ 600519  → assert_fact 报错

    OWL/Turtle 对照：
      :listedAs a owl:ObjectProperty ;
                rdfs:domain :ListedCompany ;
                rdfs:range  :Stock .
    """

    name: str  # 关系名，如 "LISTED_AS"
    domain: str  # 定义域：起点必须属于该类（或其子类）
    range: str  # 值域：终点必须属于该类（或其子类）
    min_card_on_range: int = 0  # 简化公理：range 侧每个个体至少被连几条


@dataclass
class Ontology:
    """
    【本体容器】把 TBox + ABox 装在一起的极简知识库。

    字段对应关系：
      classes      → TBox：有哪些类、父子关系
      properties   → TBox：有哪些对象属性及 domain/range
      individuals  → ABox：有哪些具体实体
      facts        → ABox：实体之间的关系三元组 (s, p, o)

    典型用法：
      onto = Ontology()
      onto.add_class("Company")
      onto.assert_fact("贵州茅台", "LISTED_AS", "600519")
    """

    classes: dict[str, OntologyClass] = field(default_factory=dict)
    properties: dict[str, ObjectProperty] = field(default_factory=dict)
    individuals: dict[str, Individual] = field(default_factory=dict)
    facts: list[tuple[str, str, str]] = field(default_factory=list)  # (s, p, o)

    def add_class(self, name: str, parent: Optional[str] = None) -> None:
        """
        向 TBox 注册一个类。

        参数：
          name   — 新类名，如 "ListedCompany"
          parent — 可选父类名；省略则视为顶层类

        副作用：
          self.classes[name] = OntologyClass(...)

        例子：
          onto.add_class("Company")
          onto.add_class("ListedCompany", parent="Company")
        """
        self.classes[name] = OntologyClass(name, parent)

    def is_subclass_of(self, child: str, ancestor: str) -> bool:
        """
        判断 child 是否是 ancestor 的子类（含自身）。

        算法：从 child 沿 parent 指针向上走，能碰到 ancestor 则 True。
        这对应本体推理里最基础的「子类继承」直觉：
          ListedCompany ⊆ Company ⇒ 茅台是 ListedCompany ⇒ 也是 Company

        参数：
          child    — 待检查的类名（或实例的 class_name）
          ancestor — 祖先类名

        返回：
          True  — child 在 ancestor 的继承链上（含 child == ancestor）
          False — 不在链上，或类未注册导致链中断

        例子：
          onto.is_subclass_of("ListedCompany", "Company")  → True
          onto.is_subclass_of("Stock", "Company")          → False
        """
        cur: Optional[str] = child
        while cur is not None:
            if cur == ancestor:
                return True
            # 取当前类的父类；若类表里没有登记，则停止上溯
            parent = self.classes[cur].parent if cur in self.classes else None
            cur = parent
        return False

    def assert_fact(self, subject: str, predicate: str, obj: str) -> None:
        """
        向 ABox 写入一条对象属性事实，并做 domain/range 约束检查。

        步骤：
          1. 确认 subject / obj / predicate 都已在本体中声明
          2. 检查起点类型是否满足属性的定义域（domain）
          3. 检查终点类型是否满足属性的值域（range）
          4. 通过则追加 (subject, predicate, obj) 到 facts

        参数：
          subject   — 起点个体名，如 "贵州茅台"
          predicate — 关系名，如 "LISTED_AS"
          obj       — 终点个体名，如 "600519"

        异常：
          ValueError — 个体或关系未声明
          TypeError  — 类型不满足 domain/range（教学上最重要的「约束生效」）

        例子：
          onto.assert_fact("贵州茅台", "LISTED_AS", "600519")  # 成功
          onto.assert_fact("某合伙企业", "LISTED_AS", "999999")  # 定义域失败
        """
        if subject not in self.individuals:
            raise ValueError(f"未知个体: {subject}")
        if obj not in self.individuals:
            raise ValueError(f"未知个体: {obj}")
        if predicate not in self.properties:
            raise ValueError(f"未知关系: {predicate}")

        prop = self.properties[predicate]
        subj = self.individuals[subject]
        obj_ind = self.individuals[obj]

        # 定义域：起点的类（或其父类）必须覆盖 prop.domain
        if not self.is_subclass_of(subj.class_name, prop.domain):
            raise TypeError(
                f"{subject} 类型 {subj.class_name} 不满足 {predicate} 的定义域 {prop.domain}"
            )
        # 值域：终点同理
        if not self.is_subclass_of(obj_ind.class_name, prop.range):
            raise TypeError(
                f"{obj} 类型 {obj_ind.class_name} 不满足 {predicate} 的值域 {prop.range}"
            )

        self.facts.append((subject, predicate, obj))

    def to_dict(self) -> dict:
        """
        把本体转成可 JSON 序列化的嵌套字典。

        结构刻意按 TBox / ABox 分层，方便对照笔记：
          {
            "TBox": { "classes": [...], "object_properties": [...] },
            "ABox": { "individuals": [...], "facts": [...] }
          }

        返回：
          dict — 仅含 str/int/list/dict/None，可直接 json.dumps
        """
        return {
            "TBox": {
                "classes": [
                    {"name": c.name, "parent": c.parent}
                    for c in self.classes.values()
                ],
                "object_properties": [
                    {
                        "name": p.name,
                        "domain": p.domain,
                        "range": p.range,
                        "min_card_on_range": p.min_card_on_range,
                    }
                    for p in self.properties.values()
                ],
            },
            "ABox": {
                "individuals": [
                    {
                        "name": i.name,
                        "class_name": i.class_name,
                        "data_props": i.data_props,
                    }
                    for i in self.individuals.values()
                ],
                "facts": [
                    {"subject": s, "predicate": p, "object": o}
                    for s, p, o in self.facts
                ],
            },
        }

    def to_json(self, indent: int = 2, ensure_ascii: bool = False) -> str:
        """
        把本体序列化成 JSON 字符串，便于打印或落盘。

        参数：
          indent       — 缩进空格数；默认 2，便于阅读
          ensure_ascii — False 时保留中文（推荐）；True 会变成 \\uXXXX

        返回：
          str — JSON 文本

        例子：
          print(onto.to_json())
        """
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=ensure_ascii)


def build_securities_ontology() -> Ontology:
    """
    构造「证券最小本体」示例（对应笔记里的三行）。

    内容：
      TBox：Company ⊇ ListedCompany；LISTED_AS: ListedCompany → Stock
      ABox：贵州茅台 —LISTED_AS→ 600519

    返回：
      已填好类、属性、个体、事实的 Ontology，可直接 demo / to_json

    学习路径：
      先看本函数怎么「建模式 + 填实例」，再看 assert_fact 如何挡非法边。
    """
    onto = Ontology()

    # --- TBox：类层次 ---
    onto.add_class("Company")
    onto.add_class("ListedCompany", parent="Company")
    onto.add_class("Stock")

    # --- TBox：对象属性 + 基数约束（Stock 侧至少 1 条入边）---
    onto.properties["LISTED_AS"] = ObjectProperty(
        name="LISTED_AS",
        domain="ListedCompany",
        range="Stock",
        min_card_on_range=1,
    )

    # --- ABox：个体 ---
    onto.individuals["贵州茅台"] = Individual("贵州茅台", "ListedCompany")
    onto.individuals["600519"] = Individual(
        "600519", "Stock", data_props={"code": "600519"}
    )

    # --- ABox：关系事实 ---
    onto.assert_fact("贵州茅台", "LISTED_AS", "600519")
    return onto


def check_cardinality(onto: Ontology) -> list[str]:
    """
    检查对象属性的「最小基数」公理是否被违反。

    本例规则：每只 Stock 至少要有一条指向它的 LISTED_AS 入边。
    违反 ⇒ 出现「孤儿股票」（有代码但挂不上公司）。

    参数：
      onto — 待检查的本体

    返回：
      问题描述列表；空列表表示通过

    算法：
      对每个 Stock 个体，统计 facts 里 object==该股票 且 predicate==LISTED_AS 的条数，
      若少于 min_card_on_range 则记一条问题。
    """
    problems: list[str] = []
    prop = onto.properties["LISTED_AS"]
    stocks = [i for i in onto.individuals.values() if i.class_name == "Stock"]
    for stock in stocks:
        incoming = [f for f in onto.facts if f[1] == "LISTED_AS" and f[2] == stock.name]
        if len(incoming) < prop.min_card_on_range:
            problems.append(f"孤儿股票: {stock.name} 缺少 LISTED_AS 入边")
    return problems


def demo() -> None:
    """
    演示入口：构建证券本体 → JSON 打印 → 子类直觉 → 基数检查 → 约束失败反例。

    建议阅读顺序：
      1. build_securities_ontology 看数据从哪来
      2. to_json 看 TBox/ABox 长什么样
      3. is_subclass_of 理解「上市公司也是公司」
      4. assert_fact 的 try/except 理解定义域约束
    """
    print("=" * 60)
    print("Ontology 学习脚本：证券最小本体")
    print("=" * 60)

    onto = build_securities_ontology()

    print("\n【onto JSON 序列化】")
    print(onto.to_json())

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

    # 子类推理直觉：显式类型是 ListedCompany，逻辑上仍属于 Company
    moutai = onto.individuals["贵州茅台"]
    print("\n【子类直觉】")
    print(f"  贵州茅台 显式类型: {moutai.class_name}")
    print(f"  是否也是 Company? {onto.is_subclass_of(moutai.class_name, 'Company')}")

    print("\n【基数约束检查】")
    problems = check_cardinality(onto)
    print("  通过" if not problems else "\n".join(f"  ! {p}" for p in problems))

    # 反例：普通 Company（非 ListedCompany）不能当 LISTED_AS 起点
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
    # 直接运行本文件时执行演示；被 import 时不会自动跑 demo
    demo()
