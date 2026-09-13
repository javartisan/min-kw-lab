#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
学习小点：EE（Event Extraction，事件抽取）
一句话：抽出「发生了什么事」——事件类型 + 论元角色。

对应笔记：docs/2-知识获取.html → EE
与 RE 差别：RE 是二元关系；EE 是「一核多论元」的结构化事件。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class Argument:
    role: str  # 论元角色：收购 / Target / Amount ...
    text: str


@dataclass
class Event:
    event_type: str
    trigger: str  # 触发词：定增、收购、并购...
    args: List[Argument] = field(default_factory=list)

    def as_graph_hints(self) -> List[str]:
        """事件如何落图：常建成 Event 节点，再连到参与实体。"""
        lines = [f"(:Event {{type:'{self.event_type}', trigger:'{self.trigger}'}})"]
        for a in self.args:
            lines.append(f"  -[:ARG_{a.role}]-> ({a.text})")
        return lines


# 事件模式：触发词 → 事件类型 + 期望角色
EVENT_SCHEMAS: Dict[str, Dict] = {
    "定增": {
        "type": "PrivatePlacement",
        "roles": ["Company", "Amount", "Purpose"],
    },
    "收购": {
        "type": "Acquisition",
        "roles": ["Buyer", "Target", "Ratio"],
    },
    "并购": {
        "type": "MAndA",
        "roles": ["Buyer", "Target"],
    },
}


def find_trigger(text: str) -> Optional[str]:
    for trigger in EVENT_SCHEMAS:
        if trigger in text:
            return trigger
    return None


def fill_args(text: str, trigger: str) -> List[Argument]:
    """
    极简槽位填充：词典 + 正则猜论元。
    生产可用：角色标注模型、问答式抽槽、LLM。
    """
    import re

    args: List[Argument] = []
    schema = EVENT_SCHEMAS[trigger]

    # 公司词典（教学冷启动）；也可用 NER 结果代替
    company_lexicon = ["贵州茅台", "宁德时代", "某电池材料公司", "五粮液"]
    companies = [c for c in company_lexicon if c in text]

    if schema["type"] == "PrivatePlacement":
        if companies:
            args.append(Argument("Company", companies[0]))
        m = re.search(r"(\d+(?:\.\d+)?)\s*亿", text)
        if m:
            args.append(Argument("Amount", m.group(0)))
        if "用于" in text:
            purpose = text.split("用于", 1)[1].split("。")[0]
            args.append(Argument("Purpose", purpose.strip()))
    elif schema["type"] in ("Acquisition", "MAndA"):
        if len(companies) >= 2:
            args.append(Argument("Buyer", companies[0]))
            args.append(Argument("Target", companies[1]))
        elif companies:
            args.append(Argument("Buyer", companies[0]))
        m = re.search(r"(\d+(?:\.\d+)?)\s*%", text)
        if m:
            args.append(Argument("Ratio", m.group(0)))

    return args


def extract_event(text: str) -> Optional[Event]:
    trigger = find_trigger(text)
    if not trigger:
        return None
    return Event(
        event_type=EVENT_SCHEMAS[trigger]["type"],
        trigger=trigger,
        args=fill_args(text, trigger),
    )


def demo() -> None:
    print("=" * 60)
    print("EE 学习脚本：事件类型 + 论元角色")
    print("=" * 60)

    samples = [
        "贵州茅台拟定增募集100亿元，用于补充流动资金。",
        "宁德时代收购某电池材料公司30%股权。",
        "今日沪指震荡收涨。（无事件）",
    ]

    for text in samples:
        print(f"\n【文本】{text}")
        ev = extract_event(text)
        if not ev:
            print("  → 未识别到事件")
            continue
        print(f"  类型={ev.event_type}  触发词={ev.trigger}")
        for a in ev.args:
            print(f"  论元 {a.role} = {a.text}")
        print("  落图示意:")
        for line in ev.as_graph_hints():
            print("   ", line)

    print("\n速记：EE 输出 (事件类型, 论元角色…)；适合公告里的定增/并购等。")


if __name__ == "__main__":
    demo()
