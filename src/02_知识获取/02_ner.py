#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
学习小点：NER（Named Entity Recognition，命名实体识别）
一句话：定位实体边界 + 打上类型标签。

对应笔记：docs/2-知识获取.html → NER
两步：Detection（从哪到哪） + Classification（是什么类）
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass
class Span:
    start: int
    end: int
    text: str
    label: str


def lexicon_ner(text: str, lexicon: dict[str, str]) -> List[Span]:
    """
    词典匹配 NER：最长优先，避免「贵州茅台」被拆成更短片段。
    生产里还会用 BiLSTM-CRF / BERT / LLM；这里把「边界+类型」讲清楚。
    """
    # 按长度降序，实现简单的最长匹配
    keys = sorted(lexicon.keys(), key=len, reverse=True)
    occupied = [False] * len(text)
    spans: List[Span] = []

    for name in keys:
        start = 0
        while True:
            idx = text.find(name, start)
            if idx < 0:
                break
            end = idx + len(name)
            # 与已占用区间重叠则跳过
            if any(occupied[idx:end]):
                start = idx + 1
                continue
            for i in range(idx, end):
                occupied[i] = True
            spans.append(Span(idx, end, name, lexicon[name]))
            start = end

    spans.sort(key=lambda s: s.start)
    return spans


def regex_stock_codes(text: str) -> List[Span]:
    """正则补充：6 位数字股票代码（A 股简化）。"""
    import re

    spans: List[Span] = []
    for m in re.finditer(r"(?<!\d)(\d{6})(?!\d)", text):
        spans.append(Span(m.start(1), m.end(1), m.group(1), "Stock"))
    return spans


def merge_spans(primary: List[Span], extra: List[Span]) -> List[Span]:
    """合并多路识别结果；词典优先，代码不与已有 span 重叠时加入。"""
    result = list(primary)
    occupied = set()
    for s in primary:
        occupied.update(range(s.start, s.end))
    for s in extra:
        if any(i in occupied for i in range(s.start, s.end)):
            continue
        result.append(s)
        occupied.update(range(s.start, s.end))
    result.sort(key=lambda s: s.start)
    return result


def demo() -> None:
    print("=" * 60)
    print("NER 学习脚本：边界 + 类型")
    print("=" * 60)

    text = "贵州茅台酒股份有限公司简称贵州茅台，股票代码600519，属于白酒。"
    lexicon = {
        "贵州茅台酒股份有限公司": "Company",
        "贵州茅台": "Company",
        "白酒": "Industry",
    }

    print(f"\n【输入】{text}")

    by_dict = lexicon_ner(text, lexicon)
    by_code = regex_stock_codes(text)
    spans = merge_spans(by_dict, by_code)

    print("\n【输出】")
    for s in spans:
        print(f"  [{s.start:02d}:{s.end:02d}] {s.text!r:20s} → {s.label}")

    print("\n【BIO 标注直觉】（深度学习标注格式）")
    # 把字符打成 B-TYPE / I-TYPE / O，帮助理解序列标注
    tags = ["O"] * len(text)
    for s in spans:
        tags[s.start] = f"B-{s.label}"
        for i in range(s.start + 1, s.end):
            tags[i] = f"I-{s.label}"
    # 只打印实体附近几个字，避免刷屏
    snippet = text[0:12]
    print("  文本:", snippet)
    print("  标签:", " ".join(tags[0:12]))

    print("\n速记：NER 输出是点；RE 负责把点连成边。")


if __name__ == "__main__":
    demo()
