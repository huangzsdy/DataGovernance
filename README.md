# TextSplit Processor

使用 LangChain 和 Celery 的文本拆分处理器。

## 功能特性

- 支持 JSON/JSONL 文件处理
- 两种输入模式：单文件和目录批量处理
- 三种文本拆分器：TokenTextSplitter、SemanticTextSplitter、HuggingFaceTokenizerSplitter
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
├── run.sh                     # 启动脚本
├── requirements.txt
└── SPEC.md
```

## 三种文本切分方法详解

### 1. TokenTextSplitter (LangChain)

基于字符级别的 token 估算进行切分。使用简单的字符计数来估算 token 数量（通常 1 个 token ≈ 4 个字符）。

**配置参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `max_tokens` | int | 1000 | 每个 chunk 的最大 token 数 |
| `overlap` | int | 100 | 相邻 chunk 之间的 token 重叠数 |

**工作原理：**
- 将文本按字符分割
- 每积累约 `max_tokens` 个字符（乘以 0.75 系数估算为 token 数）形成一个 chunk
- 相邻 chunk 之间保留 `overlap` 个 token 的重叠

**适用场景：**
- 通用文本处理
- 对精度要求不高的场景
- 需要快速处理大量文本

**配置文件示例：**
```yaml
splitter_type: "token"
token_splitter:
  max_tokens: 1000
  overlap: 100
```

---

### 2. SemanticTextSplitter (LangChain)

基于语义边界的递归字符切分器。尝试在自然语言边界（如句子、段落）处切分。

**配置参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `chunk_size` | int | 1000 | 每个 chunk 的最大字符数 |
| `buffer_size` | int | 1 | chunk 之间的重叠大小（字符数） |
| `add_start_index` | bool | false | 是否在每个 chunk 中添加起始位置索引 |
| `separators` | list | 见下方 | 分隔符列表（按优先级排序） |

**默认分隔符顺序：**
```python
["\n\n", "\n", "。", "！", "？", ". ", "！", "？", " ", ""]
```

**工作原理：**
- 按分隔符列表顺序尝试切分文本
- 先尝试在段落边界（`\n\n`）切分
- 再尝试在句子边界（如句号、问号）切分
- 最后在单词边界（空格）切分

**适用场景：**
- 保留语义完整的句子
- 需要良好的阅读体验
- 中英文混合文本

**配置文件示例：**
```yaml
splitter_type: "semantic"
semantic_splitter:
  chunk_size: 1000
  buffer_size: 1
  add_start_index: false
```

---

### 3. HuggingFaceTokenizerSplitter (推荐)

使用 HuggingFace Tokenizer 进行精确 token 统计和切分。参考 NVIDIA NeMo Curator 的方法。

**配置参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `max_tokens` | int | 1000 | 每个 chunk 的最大 token 数 |
| `overlap` | int | 100 | 相邻 chunk 之间的 token 重叠数 |
| `hf_model_name` | str | "bert-base-uncased" | HuggingFace 模型名称，用于加载对应 tokenizer |

**工作原理：**
1. 使用 HuggingFace Tokenizer 进行精确 token 计数
2. 先按句子分隔符拆分为句子列表
3. 逐句累加 token 数，达到 `max_tokens` 限制时创建新 chunk
4. 支持 chunk 之间的 token overlap

**支持的 Tokenizer 模型：**
- `bert-base-uncased` - 英文为主
- `bert-base-chinese` - 中文
- `gpt2` - GPT-2 tokenizer
- `cl100k_base` - GPT-4/Claude 使用
- 其他 HuggingFace 上的任何 tokenizer

**适用场景：**
- 需要精确控制 token 数量
- 大语言模型训练数据处理
- 多语言文本处理
- 对 token 统计精度要求高的场景

**配置文件示例：**
```yaml
splitter_type: "tokenizer"
tokenizer_splitter:
  max_tokens: 1000
  overlap: 100
  hf_model_name: "bert-base-uncased"
```

**推荐配置：**

对于中文文本，建议使用中文 tokenizer：
```yaml
tokenizer_splitter:
  max_tokens: 1000
  overlap: 100
  hf_model_name: "bert-base-chinese"
```

---

## 配置文件说明

```yaml
# 处理模式: "single" - 单文件模式, "directory" - 目录模式
mode: "single"

# 文件路径
input_path: "data/input.jsonl"
output_path: "data/output.jsonl"

# 文本拆分器类型: "token", "semantic", 或 "tokenizer"
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
  add_start_index: false

# HuggingFaceTokenizerSplitter 参数
tokenizer_splitter:
  max_tokens: 1000
  overlap: 100
  hf_model_name: "bert-base-uncased"

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