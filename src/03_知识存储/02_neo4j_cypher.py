#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
学习小点：Neo4j + Cypher
一句话：属性图引擎；App 经 Bolt 连接，用 Cypher 声明式读写。

对应笔记：docs/3-知识存储.html → Neo4j
本脚本不连真实 Neo4j，而是：打印标准 Cypher + 用内存图执行等价操作。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class MiniNeo4j:
    """教学用「假 Neo4j」：理解 MERGE / MATCH 语义。"""

    def __init__(self) -> None:
        # key = (label, name) → props
        self.entities: Dict[tuple, Dict[str, Any]] = {}
        # (from_name, type, to_name) → props
        self.rels: Dict[tuple, Dict[str, Any]] = {}

    def merge_entity(self, label: str, name: str, **props: Any) -> Dict[str, Any]:
        """
        对应：
          MERGE (c:Company {name: $name})
          ON CREATE SET c.id = $id
        """
        key = (label, name)
        if key not in self.entities:
            node = {"name": name, "label": label, **props}
            self.entities[key] = node
            print(f"  [ON CREATE] (:{label} {{name:{name!r}}})")
        else:
            self.entities[key].update(props)
            print(f"  [MATCH已有] (:{label} {{name:{name!r}}})")
        return self.entities[key]

    def merge_rel(self, a_name: str, typ: str, b_name: str, **props: Any) -> None:
        key = (a_name, typ, b_name)
        if key not in self.rels:
            self.rels[key] = props
            print(f"  [CREATE REL] ({a_name})-[:{typ}]->({b_name})")
        else:
            self.rels[key].update(props)
            print(f"  [REL已有] ({a_name})-[:{typ}]->({b_name})")

    def match(self, name_contains: str) -> List[tuple]:
        """对应：MATCH (n)-[r]->(m) WHERE n.name CONTAINS $kw RETURN n,r,m"""
        hits = []
        for (a, typ, b), props in self.rels.items():
            if name_contains in a:
                hits.append((a, typ, b, props))
        return hits


# 真实项目里会发给 Neo4j 的 Cypher 模板（务必参数化！）
CYPHER_TEMPLATES = {
    "merge_company": """
MERGE (c:Entity:Company {name: $name, entityType: 'Company'})
ON CREATE SET c.id = $id, c.createdAt = datetime()
""",
    "merge_belongs_to": """
MATCH (a:Entity {name: $from}), (b:Entity {name: $to})
MERGE (a)-[r:BELONGS_TO]->(b)
""",
    "query_keyword": """
MATCH (n:Entity)-[r]->(m:Entity)
WHERE n.name CONTAINS $keyword
RETURN n, r, m
""",
    "controls_path": """
MATCH path = (a:Company)-[:CONTROLS*1..3]->(b)
RETURN path
""",
}


def demo() -> None:
    print("=" * 60)
    print("Neo4j/Cypher 学习脚本：MERGE 语义 + 查询模板")
    print("=" * 60)

    print("\n【连接直觉】App --Bolt--> bolt://localhost:7687")

    print("\n【常用 Cypher 模板】")
    for name, q in CYPHER_TEMPLATES.items():
        print(f"\n-- {name}")
        print(q.strip())

    print("\n【内存模拟执行】")
    db = MiniNeo4j()
    db.merge_entity("Company", "贵州茅台", id="c1")
    db.merge_entity("Company", "贵州茅台", id="c1")  # 第二次应复用
    db.merge_entity("Industry", "白酒", id="i1")
    db.merge_rel("贵州茅台", "BELONGS_TO", "白酒")

    print("\n【查询 name CONTAINS '茅台'】")
    for row in db.match("茅台"):
        print(f"  {row}")

    print("\n安全要点：名称用 $参数绑定，禁止把用户输入拼进 Cypher 字符串。")


if __name__ == "__main__":
    demo()
