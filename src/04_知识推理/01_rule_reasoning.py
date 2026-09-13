#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
学习小点：规则推理（Rule-based Reasoning）
一句话：IF 条件模式成立 THEN 断言新事实 / 告警。

对应笔记：docs/4-知识推理.html → 规则推理
强项：可解释、易嵌入风控；坑：规则冲突与维护成本。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Set, Tuple


Fact = Tuple[str, str, str]  # (s, p, o)


@dataclass
class RuleEngine:
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
        """前向链：反复应用规则直到不动点（深度有限）。"""
        # R1 控股传递（简化，只物化一层间接，避免爆炸）
        # IF (a)-CONTROLS->(b) AND (b)-CONTROLS->(c) THEN (a)-CONTROLS_INDIRECT->(c)
        for a, _, b in self.match(p="CONTROLS"):
            for _, _, c in self.match(s=b, p="CONTROLS"):
                self.assert_fact(a, "CONTROLS_INDIRECT", c, inferred=True)

        # R2 上市推断：有 LISTED_AS → 标记为 ListedCompany
        for x, _, s in self.match(p="LISTED_AS"):
            self.assert_fact(x, "rdf:type", "ListedCompany", inferred=True)

        # R3 风控：同一人任职两家竞品公司
        # (p)-HAS_EXECUTIVE_OF->(c1), (p)-HAS_EXECUTIVE_OF->(c2), (c1)-COMPETES_WITH-(c2)
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


def demo() -> None:
    print("=" * 60)
    print("规则推理学习脚本：传递 / 类型推断 / 风控告警")
    print("=" * 60)

    eng = RuleEngine()
    # 显式事实
    eng.assert_fact("茅台集团", "CONTROLS", "贵州茅台")
    eng.assert_fact("贵州茅台", "CONTROLS", "某销售子公司")
    eng.assert_fact("贵州茅台", "LISTED_AS", "600519")
    eng.assert_fact("丁某", "HAS_EXECUTIVE_OF", "贵州茅台")
    eng.assert_fact("丁某", "HAS_EXECUTIVE_OF", "五粮液")
    eng.assert_fact("贵州茅台", "COMPETES_WITH", "五粮液")

    print("\n【显式事实】")
    for f in sorted(eng.facts):
        print(f"  {f}")

    eng.run()

    print("\n【推出事实】")
    for f in eng.inferred:
        print(f"  {f}")

    print("\n【告警】")
    for a in eng.alerts:
        print(f"  ! {a}")

    print(
        "\n注意：不要盲目物化全部传递闭包；高频规则可物化，其余查询时计算。"
    )
    print("速记：按人定的 IF-THEN，从图里推出新结论——适合要审计解释的场景。")


if __name__ == "__main__":
    demo()
