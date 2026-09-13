# -*- coding: utf-8 -*-
"""
证券学习种子图谱（写入 Neo4j）

工程要点：
  - 所有节点带 lab=$lab，脚本只动学习数据，不 DROP 整库
  - MERGE + 唯一业务键（name / code），幂等可重复跑
  - 关系类型与 docs / 问答 / 分析脚本约定一致
"""

from __future__ import annotations

from typing import Any

from .neo4j_client import get_lab_tag, run_cypher


# 节点：(label, name, extra_props)
_COMPANIES = [
    ("Company", "贵州茅台", {"entityType": "Company", "listed": True}),
    ("Company", "五粮液", {"entityType": "Company", "listed": True}),
    ("Company", "宁德时代", {"entityType": "Company", "listed": True}),
    ("Company", "茅台集团", {"entityType": "Company", "listed": False}),
    ("Company", "某销售子公司", {"entityType": "Company", "listed": False}),
]

_STOCKS = [
    ("Stock", "600519", {"code": "600519", "entityType": "Stock"}),
    ("Stock", "000858", {"code": "000858", "entityType": "Stock"}),
    ("Stock", "300750", {"code": "300750", "entityType": "Stock"}),
]

_INDUSTRIES = [
    ("Industry", "白酒", {"entityType": "Industry"}),
    ("Industry", "动力电池", {"entityType": "Industry"}),
]

_PEOPLE = [
    ("Person", "丁雄军", {"entityType": "Person", "title": "董事长"}),
]

_DOCS = [
    ("Document", "研报A", {"entityType": "Document"}),
]

# (from_name, from_label, rel, to_name, to_label, props)
_RELS: list[tuple[str, str, str, str, str, dict[str, Any]]] = [
    ("贵州茅台", "Company", "LISTED_AS", "600519", "Stock", {}),
    ("五粮液", "Company", "LISTED_AS", "000858", "Stock", {}),
    ("宁德时代", "Company", "LISTED_AS", "300750", "Stock", {}),
    ("贵州茅台", "Company", "BELONGS_TO", "白酒", "Industry", {}),
    ("五粮液", "Company", "BELONGS_TO", "白酒", "Industry", {}),
    ("宁德时代", "Company", "BELONGS_TO", "动力电池", "Industry", {}),
    ("贵州茅台", "Company", "HAS_EXECUTIVE", "丁雄军", "Person", {}),
    ("贵州茅台", "Company", "COMPETES_WITH", "五粮液", "Company", {}),
    ("茅台集团", "Company", "CONTROLS", "贵州茅台", "Company", {"ratio": 0.54}),
    ("贵州茅台", "Company", "CONTROLS", "某销售子公司", "Company", {"ratio": 1.0}),
    ("研报A", "Document", "MENTIONS", "贵州茅台", "Company", {}),
    ("研报A", "Document", "MENTIONS", "白酒", "Industry", {}),
]


def clear_lab_graph() -> int:
    """只删除 lab 标记的学习子图。"""
    lab = get_lab_tag()
    rows = run_cypher(
        """
        MATCH (n {lab: $lab})
        DETACH DELETE n
        RETURN count(*) AS deleted
        """,
        {"lab": lab},
        write=True,
    )
    return int(rows[0]["deleted"]) if rows else 0


def _merge_node(label: str, name: str, props: dict[str, Any]) -> None:
    lab = get_lab_tag()
    # 标签不能参数化，白名单拼接
    allowed = {"Company", "Stock", "Industry", "Person", "Document"}
    if label not in allowed:
        raise ValueError(f"不允许的标签: {label}")
    run_cypher(
        f"""
        MERGE (n:{label} {{name: $name, lab: $lab}})
        ON CREATE SET n.createdAt = datetime()
        SET n += $props
        SET n.lab = $lab
        """,
        {"name": name, "lab": lab, "props": props},
        write=True,
    )


def _merge_rel(
    a_name: str,
    a_label: str,
    rel: str,
    b_name: str,
    b_label: str,
    props: dict[str, Any],
) -> None:
    lab = get_lab_tag()
    allowed_rel = {
        "LISTED_AS",
        "BELONGS_TO",
        "HAS_EXECUTIVE",
        "COMPETES_WITH",
        "CONTROLS",
        "CONTROLS_INDIRECT",
        "MENTIONS",
        "SAME_AS",
    }
    if rel not in allowed_rel:
        raise ValueError(f"不允许的关系: {rel}")
    run_cypher(
        f"""
        MATCH (a:{a_label} {{name: $a, lab: $lab}})
        MATCH (b:{b_label} {{name: $b, lab: $lab}})
        MERGE (a)-[r:{rel}]->(b)
        SET r += $props
        SET r.lab = $lab
        """,
        {"a": a_name, "b": b_name, "lab": lab, "props": props},
        write=True,
    )


def ensure_seed_graph(*, reset: bool = False) -> dict[str, int]:
    """
    确保学习用证券子图存在。
    reset=True 时先清 lab 子图再写入（幂等演示用）。
    """
    if reset:
        clear_lab_graph()

    for label, name, props in _COMPANIES + _STOCKS + _INDUSTRIES + _PEOPLE + _DOCS:
        _merge_node(label, name, props)

    for a, al, rel, b, bl, props in _RELS:
        _merge_rel(a, al, rel, b, bl, props)

    lab = get_lab_tag()
    stats = run_cypher(
        """
        MATCH (n {lab: $lab})
        OPTIONAL MATCH (n)-[r {lab: $lab}]->()
        RETURN count(DISTINCT n) AS nodes, count(r) AS rels
        """,
        {"lab": lab},
    )
    return {
        "lab": lab,
        "nodes": int(stats[0]["nodes"]),
        "rels": int(stats[0]["rels"]),
    }


def main() -> None:
    from .neo4j_client import require_neo4j

    with require_neo4j():
        s = ensure_seed_graph(reset=True)
        print(f"种子图谱已就绪: lab={s['lab']} nodes={s['nodes']} rels={s['rels']}")


if __name__ == "__main__":
    main()
