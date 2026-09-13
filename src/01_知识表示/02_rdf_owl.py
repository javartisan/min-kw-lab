#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ↑ 指定用 python3 解释器运行；声明源文件为 UTF-8，支持中文注释与字符串
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

from __future__ import annotations  # 允许类型注解里写 list[str]、str | None 等现代写法（兼容旧运行时解析）

from dataclasses import dataclass, field  # dataclass：少写样板代码；field：给可变默认值（如 list）安全初始化


# ---------------------------------------------------------------------------
# RDF：一切皆三元组 (Subject, Predicate, Object)
# ---------------------------------------------------------------------------

# 教学简化：用短名字符串代替完整 IRI
# 真实工程里应是 http://example.org/sec#Moutai 这类全球唯一标识
Triple = tuple[str, str, str]  # 类型别名：一条三元组 = (主语str, 谓语str, 宾语str)


@dataclass  # 自动生成 __init__ / __repr__ 等，把下面字段变成实例属性
class RdfGraph:
    """
    【迷你 RDF 图】内存中的三元组集合。

    真实系统对应：Jena Model / RDF4J Repository / Neo4j 里导出的 RDF 等。
    本类只保留「存三元组 + 按模式查询」两个核心动作，方便理解 RDF 模型。

    字段：
      triples — [(主语, 谓语, 宾语), ...]，顺序即插入顺序
    """

    # 图的全部内容：三元组列表；default_factory=list 表示每个实例各自新建空列表（避免共享可变默认值）
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
        self.triples.append((s, p, o))  # 把 (主语, 谓语, 宾语) 元组追加到图末尾

    def ask(
        self,  # 当前 RDF 图实例
        s: str | None = None,  # 可选：限定主语；None 表示该位通配
        p: str | None = None,  # 可选：限定谓语；None 表示该位通配
        o: str | None = None,  # 可选：限定宾语；None 表示该位通配
    ) -> list[Triple]:  # 返回所有命中的三元组
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
        out: list[Triple] = []  # 存放查询命中结果
        for t in self.triples:  # 逐条扫描图中已有三元组（教学用暴力匹配）
            if s is not None and t[0] != s:  # 若指定了主语且当前主语不匹配 → 跳过
                continue  # 进入下一条三元组
            if p is not None and t[1] != p:  # 若指定了谓语且当前谓语不匹配 → 跳过
                continue
            if o is not None and t[2] != o:  # 若指定了宾语且当前宾语不匹配 → 跳过
                continue
            out.append(t)  # 三个位置都通过（或通配）→ 记为命中
        return out  # 返回命中列表（可能为空列表）


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
    g = RdfGraph()  # 新建一张空的内存 RDF 图

    # ----- TBox：术语 / 模式 -----
    g.add("ListedCompany", "rdfs:subClassOf", "Company")  # 公理：上市公司是公司的子类
    g.add("Person", "owl:disjointWith", "Company")  # 公理：人与公司互斥（不能同时成立）
    g.add("listedAs", "rdfs:domain", "ListedCompany")  # 公理：listedAs 的起点必须是上市公司
    g.add("listedAs", "rdfs:range", "Stock")  # 公理：listedAs 的终点必须是股票

    # ----- ABox：断言 / 实例 -----
    g.add("Moutai", "rdf:type", "ListedCompany")  # 事实：茅台是上市公司实例
    g.add("Moutai", "listedAs", "S600519")  # 事实：茅台上市为股票 S600519
    g.add("S600519", "rdf:type", "Stock")  # 事实：S600519 是股票实例
    g.add("Moutai", "rdfs:label", "贵州茅台")  # 事实：给人看的中文标签（字面量）
    return g  # 返回已填充显式三元组的图（此时还没有「推出」的隐含类型）


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
    inferred: list[Triple] = []  # 只收集「新推出」的三元组，便于和显式事实对比
    known = set(g.triples)  # 把已有三元组放进集合，便于 O(1) 判断是否已存在

    changed = True  # 标记本轮是否推出了新事实；用于控制是否继续迭代
    while changed:  # 反复推理直到某一轮没有任何新增（达到不动点）
        changed = False  # 先假定本轮无新增；下面一旦新增就改回 True
        # 从当前 known 中抽出所有「类型断言」：(个体, 类)
        type_facts = [(s, o) for s, p, o in known if p == "rdf:type"]
        # 从当前 known 中抽出所有「子类公理」：(子类, 父类)
        subclass = [(s, o) for s, p, o in known if p == "rdfs:subClassOf"]
        for x, c in type_facts:  # 遍历：个体 x 属于类 c
            for child, parent in subclass:  # 遍历：child 是 parent 的子类
                if c == child:  # 若 x 的类恰好是某个子类 child
                    neo = (x, "rdf:type", parent)  # 则推出：x 也应属于父类 parent
                    if neo not in known:  # 若这条推出还没出现过
                        known.add(neo)  # 记入 known，供后续轮次继续传递
                        inferred.append(neo)  # 同时记入「新推出」列表，供 demo 打印
                        changed = True  # 有新增 → 可能还能再推出更上层父类，继续 while
    return inferred  # 返回本函数新推出的全部类型三元组


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
    # 显式事实 ∪ 推出事实 = 推理器眼中的完整知识（至少类型相关部分）
    all_triples = set(g.triples) | set(inferred)

    types: dict[str, set[str]] = {}  # 映射：实体名 → 它拥有的类型集合
    for s, p, o in all_triples:  # 扫描全部三元组
        if p == "rdf:type":  # 只关心类型断言
            types.setdefault(s, set()).add(o)  # 若实体首次出现则建空集合，再加入类型 o

    # 取出所有「A 与 B 互斥」对
    disjoint_pairs = [(s, o) for s, p, o in all_triples if p == "owl:disjointWith"]
    # 互斥对称：有 (A,B) 就补上 (B,A)，避免漏检
    pairs = set(disjoint_pairs) | {(b, a) for a, b in disjoint_pairs}

    conflicts: list[str] = []  # 收集不一致描述
    for entity, tset in types.items():  # 检查每一个实体的类型集合
        for a, b in pairs:  # 对照每一对互斥类
            if a in tset and b in tset:  # 若实体同时具有互斥的两类
                conflicts.append(f"{entity} 同时是 {a} 与 {b} → 不一致")  # 记录冲突
    return conflicts  # 空列表 = 一致；非空 = 发现矛盾


def demo() -> None:
    """
    演示入口：显式三元组 → 子类推理补全 → 一致性 OK → 故意制造冲突。

    对照学习：
      1. load_securities_facts  = 读 .ttl 里「写死」的内容
      2. rdfs_type_closure     = Protégé 里 Inferred 多出来的类型
      3. check_disjoint        = 推理器报 inconsistent
    """
    print("=" * 60)  # 打印分隔线，方便在终端里分段阅读
    print("RDF/OWL 学习脚本：三元组 + 子类推理 + 互斥校验")  # 标题
    print("=" * 60)  # 再打一条分隔线

    g = load_securities_facts()  # 加载证券迷你本体的显式 TBox+ABox
    print("\n【显式三元组】")  # 小节标题：尚未推理的原始断言
    for t in g.triples:  # 遍历图中每一条显式三元组
        print(f"  {t[0]}  —{t[1]}→  {t[2]}")  # 按「主语 —谓语→ 宾语」格式打印

    inferred = rdfs_type_closure(g)  # 跑 RDFS 子类规则，得到新推出的类型
    print("\n【RDFS 推出】（未写入、由公理得到）")  # 小节标题：推理结果
    for t in inferred:  # 遍历每条推出的三元组
        print(f"  {t[0]}  —{t[1]}→  {t[2]}   # Moutai 因 ListedCompany⊆Company")  # 打印并提示来源

    print("\n【一致性】当前应无冲突")  # 此时茅台只有公司侧类型，应一致
    print(" ", check_disjoint(g, inferred) or "OK")  # 有冲突打印列表，否则打印 OK

    # 故意制造冲突：再断言茅台是 Person（与 Company 互斥）
    print("\n【冲突演示】再断言 Moutai rdf:type Person")  # 小节标题
    g.add("Moutai", "rdf:type", "Person")  # 向 ABox 追加冲突断言
    inferred2 = rdfs_type_closure(g)  # 重新推理（Person 断言本身通常不再推出 Company）
    print(" ", check_disjoint(g, inferred2))  # 应打印「同时是 Person 与 Company」类冲突

    print(  # 收尾速记：三条学习主线
        "\n速记：Ontology 定语义 → RDF 落三元组 → OWL 公理交给推理器；"
        "完整 Turtle 见 docs/examples/securities-mini.ttl"
    )


if __name__ == "__main__":  # 仅当本文件被直接运行时为 True（被 import 时不执行）
    demo()  # 启动完整演示流程
