# 知识图谱 · 七大方向学习脚本

对应 `docs/index.html`。每个文件夹 = 一个技术方向；每个脚本 = 一个学习小点。

## Neo4j 工程实践（需你手动启动库）

与图库相关的脚本已改为走 **真实 Bolt + 官方 Driver**，不再用假库冒充。

1. 安装依赖（虚拟环境）：

```bash
source venv/bin/activate
pip install -r requirements.txt
```

2. 配置连接：复制 `.env.example` → `.env`（仓库已有默认 `neo4j/password`），按你本机改密码。

3. **手动启动** Neo4j（本仓库不代启）：

```bash
# 任选其一
docker compose up -d
# 或 Neo4j Desktop / 你已有的实例，保证 bolt://localhost:7687 可连
```

4. 写入证券学习种子图（带 `lab=min-kw-lab`，不碰其它业务数据）：

```bash
source venv/bin/activate
PYTHONPATH=src python -m common.seed_kg
```

5. 跑需要图库的脚本，例如：

```bash
PYTHONPATH=src python src/03_知识存储/02_neo4j_cypher.py
PYTHONPATH=src python src/06_知识问答/01_kbqa.py
PYTHONPATH=src python src/07_知识分析/02_metrics_insight.py
```

连不上时脚本会打印 URI/指引并退出，不会静默假成功。

### 哪些脚本连 Neo4j？

| 目录 | 脚本 | 行为 |
|------|------|------|
| 03 存储 | `01_graph_database` / `02_neo4j_cypher` | 模型讲解 + 真实 MERGE/MATCH/多跳 |
| 02 获取 | `01_nlp_pipeline --neo4j` | 可选：抽取结果入库 |
| 04 推理 | `01_rule_reasoning` | Cypher 物化推断边 |
| 06 问答 | `01_kbqa` / `02_semantic_parsing` / `03_graph_rag` | 查真图作答 |
| 07 分析 | 三个脚本 | 指标/路径/导出 JSON |

其余（表示、RDF 内存、OWL 推理直觉、Embedding、融合算法等）保持纯 Python，聚焦概念。

## 纯概念脚本（无需 Neo4j）

```bash
python src/01_知识表示/01_ontology.py
```

## 设计约定

- 示例统一证券领域；学习节点一律带 `lab` 属性隔离。
- Cypher **参数化**（`$name`），禁止拼接用户输入。
- 注释讲「为什么」；共享逻辑在 `src/common/`。
