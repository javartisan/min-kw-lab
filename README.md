# min-kw-lab

知识图谱七大方向学习实验：`docs/` 笔记 + `src/` 可运行脚本。

图库相关脚本已对接 **Neo4j Bolt**（需自行启动）。详见 [`src/README.md`](src/README.md)。

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
# 手动启动 Neo4j 后：
PYTHONPATH=src python -m common.seed_kg
```
