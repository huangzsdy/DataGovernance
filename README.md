# TextSplit Processor

使用 LangChain 和 Celery 的文本拆分处理器。

## 功能特性

- 支持 JSON/JSONL 文件处理
- 两种输入模式：单文件和目录批量处理
- 两种文本拆分器：TokenTextSplitter 和 SemanticTextSplitter
- 基于 Celery 异步任务处理

## 项目结构

```
text_split_processor/
├── config/
│   └── settings.yaml          # 配置文件
├── src/
│   ├── __init__.py
│   ├── main.py                # 入口文件
│   ├── celery_app.py          # Celery 应用配置
│   ├── tasks.py               # Celery 任务定义
│   ├── processors/
│   │   ├── __init__.py
│   │   ├── text_splitter.py   # 文本拆分器
│   │   └── file_processor.py  # 文件处理器
│   └── utils/
│       ├── __init__.py
│       └── logger.py          # 日志工具
├── requirements.txt
└── SPEC.md
```

## 配置文件说明

```yaml
# 处理模式: "single" - 单文件模式, "directory" - 目录模式
mode: "single"

# 文件路径
input_path: "data/input.jsonl"
output_path: "data/output.jsonl"

# 文本拆分器类型: "token" 或 "semantic"
splitter_type: "token"

# 要处理的 content 字段名
content_field: "content"

# TokenTextSplitter 参数
token_splitter:
  max_tokens: 1000
  overlap: 100

# SemanticTextSplitter 参数
semantic_splitter:
  chunk_size: 1000
  buffer_size: 1

# Celery 配置
celery:
  broker: "redis://localhost:6379/0"
  backend: "redis://localhost:6379/1"
```

## 安装依赖

```bash
pip install -r requirements.txt
```

## 使用方法

### 1. 启动 Redis

```bash
# 使用 Docker
docker run -d -p 6379:6379 redis

# 或直接安装 Redis
```

### 2. 启动 Celery Worker

```bash
celery -A src.celery_app worker --loglevel=info
```

### 3. 提交任务

#### 方式一：命令行

```bash
# 单文件模式
python -m src.main --config config/settings.yaml

# 目录模式
python -m src.main --config config/settings.yaml --mode directory

# 同步运行（无需 Celery）
python -m src.main --config config/settings.yaml --sync
```

#### 方式二：Python 代码

```python
from src.main import run_single_file, run_directory, run_sync

# 异步任务
result = run_single_file("config/settings.yaml")

# 同步运行
result = run_sync("config/settings.yaml")
```

## 输入输出示例

### 输入文件 (input.jsonl)

```json
{"id": 1, "content": "这是第一句话。这是第二句话。这是第三句话。", "category": "A"}
{"id": 2, "content": "第四句。第五句。第六句。", "category": "B"}
```

### 输出文件 (input_textSplit.jsonl)

```json
{"id": 1, "content": "这是第一句话。这是第二句话。这是第三句话。", "category": "A", "split_content": "这是第一句话。"}
{"id": 1, "content": "这是第一句话。这是第二句话。这是第三句话。", "category": "A", "split_content": "这是第二句话。"}
{"id": 1, "content": "这是第一句话。这是第二句话。这是第三句话。", "category": "A", "split_content": "这是第三句话。"}
{"id": 2, "content": "第四句。第五句。第六句。", "category": "B", "split_content": "第四句。"}
{"id": 2, "content": "第四句。第五句。第六句。", "category": "B", "split_content": "第五句。"}
{"id": 2, "content": "第四句。第五句。第六句。", "category": "B", "split_content": "第六句。"}
```