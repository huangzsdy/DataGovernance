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

### 3. HuggingFaceTokenizerSplitter

使用 HuggingFace Tokenizer 进行精确 token 统计和切分。参考 NVIDIA NeMo Curator 的方法。

**配置参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `max_tokens` | int | 1000 | 每个 chunk 的最大 token 数 |
| `overlap` | int | 100 | 相邻 chunk 之间的 token 重叠数 |
| `hf_model_name` | str | 自动选择 | HuggingFace 模型名称，用于加载对应 tokenizer |
| `language` | str | "en" | 语言代码，自动选择对应 tokenizer 和分隔符 |

**工作原理：**
1. 使用 HuggingFace Tokenizer 进行精确 token 计数
2. 先按语言特定的分隔符拆分为句子列表
3. 逐句累加 token 数，达到 `max_tokens` 限制时创建新 chunk
4. 支持 chunk 之间的 token overlap
5. 自动处理超长句子（按字符切分）

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
  language: "en"
```

**推荐配置：**

对于中文文本，建议使用中文 tokenizer：
```yaml
tokenizer_splitter:
  max_tokens: 1000
  overlap: 100
  hf_model_name: "bert-base-chinese"
  language: "zh"
```

---

### 4. PySBDSplitter (推荐)

使用 **pysbd** (Python Sentence Boundary Detection) 进行专业的多语言句子分割。

**pysbd 特点：**
- 支持 **60+ 语言**的精确句子分割
- 基于语言规则，准确处理缩写、书名号、括号等边界情况
- 比正则表达式更准确的句子边界检测
- 支持中文、日文、阿拉伯文、希伯来文等复杂语言

**配置参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `max_tokens` | int | 1000 | 每个 chunk 的最大 token 数 |
| `overlap` | int | 100 | 相邻 chunk 之间的 token 重叠数 |
| `language` | str | "en" | 语言代码 (ISO 639-1) |
| `language_is_code` | bool | true | language 是否为语言代码 |

**支持的语言：**
- `en` 英语、`es` 西班牙语、`fr` 法语、`de` 德语
- `zh` 中文、`ja` 日语、`ko` 韩语
- `ar` 阿拉伯语、`he` 希伯来语
- `hi` 印地语、`bn` 孟加拉语
- 以及 60+ 其他语言

**配置文件示例：**
```yaml
splitter_type: "pysbd"
pysbd_splitter:
  max_tokens: 1000
  overlap: 100
  language: "en"
```

**语言对应表：**

| 语言 | language 值 | 说明 |
|------|-------------|------|
| 中文 | "zh" | 精确按句子切分 |
| 英文 | "en" | 正确处理缩写 (如 Dr., U.S.A.) |
| 西班牙语 | "es" | 正确处理 ¡ ¿ 等特殊符号 |
| 阿拉伯语 | "ar" | 从右向左文本 |
| 希伯来语 | "he" | 从右向左文本 |
| 日语 | "ja" | 正确处理句子边界 |
| 印地语 | "hi" | 使用梵文句号 |

---

## 小语种文本切分方案

本项目支持多种语言的文本切分，包括西班牙语、希伯来语、阿拉伯语、印地语等小语种。

### 支持的语言

| 语言代码 | 语言名称 | 推荐 Tokenizer | 特殊分隔符 |
|----------|----------|----------------|------------|
| `en` | 英语 | bert-base-uncased | `.`, `?`, `!` |
| `es` | 西班牙语 | bert-base-multilingual-cased | `.`, `?`, `!` |
| `fr` | 法语 | bert-base-multilingual-cased | `.`, `?`, `!` |
| `de` | 德语 | bert-base-multilingual-cased | `.`, `?`, `!` |
| `pt` | 葡萄牙语 | bert-base-multilingual-cased | `.`, `?`, `!` |
| `ru` | 俄语 | bert-base-multilingual-cased | `.`, `?`, `!` |
| `he` | 希伯来语 | bert-base-hebrew | `.`, `?`, `׃` |
| `ar` | 阿拉伯语 | asafaya/bert-base-arabic | `.`, `?`, `!`, `؛` |
| `hi` | 印地语 | ai4bharat/IndicBERT | `।`, `?`, `!` |
| `bn` | 孟加拉语 | ai4bharat/IndicBERT | `।`, `?`, `!` |
| `zh` | 中文 | bert-base-chinese | `。`, `！`, `？` |
| `ja` | 日语 | bert-base-japanese | `。`, `！`, `？` |
| `ko` | 韩语 | beomi/kcbert-base | `.`, `!`, `?` |
| `th` | 泰语 | bool/boolbert-thai | `।`, `?`, `!` |
| `vi` | 越南语 | bert-base-multilingual-cased | `.`, `?`, `!` |
| `id` | 印尼语 | bert-base-multilingual-cased | `.`, `?`, `!` |
| `sw` | 斯瓦希里语 | bert-base-multilingual-cased | `.`, `?`, `!` |
| `multi` | 多语言混合 | bert-base-multilingual-cased | 综合多种语言分隔符 |

### 使用方法

#### 方式一：通过配置文件指定语言

```yaml
# 西班牙语
splitter_type: "tokenizer"
tokenizer_splitter:
  max_tokens: 1000
  overlap: 100
  language: "es"
  # hf_model_name 会自动根据 language 选择

# 希伯来语
splitter_type: "tokenizer"
tokenizer_splitter:
  max_tokens: 1000
  overlap: 100
  language: "he"

# 阿拉伯语
splitter_type: "tokenizer"
tokenizer_splitter:
  max_tokens: 1000
  overlap: 100
  language: "ar"

# 印地语
splitter_type: "tokenizer"
tokenizer_splitter:
  max_tokens: 1000
  overlap: 100
  language: "hi"
```

#### 方式二：自定义 Tokenizer 和分隔符

如果内置的语言配置不满足需求，可以手动指定：

```yaml
splitter_type: "tokenizer"
tokenizer_splitter:
  max_tokens: 1000
  overlap: 100
  # 自定义 tokenizer 模型
  hf_model_name: "xlm-roberta-base"
  # 自定义分隔符（覆盖 language 设置）
  # separators: ["\n\n", "\n", ". ", "? ", "! ", " "]
```

### 小语种注意事项

1. **西班牙语 (es)**
   - 标点与英语相同，`.` `?` `!` 均可正确识别
   - 某些文本可能包含 `¡`（反感叹号），需注意

2. **希伯来语 (he)**
   - 希伯来语从右向左书写
   - 句号 `.` 可以正确识别
   - 特殊符号 `׃`（犹太教符号）也作为句子结束符

3. **阿拉伯语 (ar)**
   - 类似地从右向左书写
   - 使用 `؛`（阿拉伯分号）和 `،`（阿拉伯逗号）
   - 建议使用专门的 Arabic tokenizer

4. **印地语/孟加拉语等印度语言**
   - 使用 `।`（梵文感叹号）作为句号
   - 需要使用 `ai4bharat/IndicBERT` 等专门的 tokenizer

5. **多语言混合文本**
   - 使用 `language: "multi"` 或 `bert-base-multilingual-cased`
   - 会尝试匹配多种语言的分隔符

### 超长句子处理

当单个句子超过 `max_tokens` 时，HuggingFaceTokenizerSplitter 会自动：
1. 先保存当前 chunk
2. 将长句按字符切分为多个小块
3. 继续处理后续文本

这确保了即使面对超长句子也不会丢失数据。

### 运行示例

```bash
# 处理西班牙语文本
bash run.sh --splitter tokenizer

# 处理希伯来语文本
# 配置文件设置 language: "he"

---

## 配置文件说明

```yaml
# 处理模式: "single" - 单文件模式, "directory" - 目录模式
mode: "single"

# 文件路径
input_path: "data/input.jsonl"
output_path: "data/output.jsonl"

# 文本拆分器类型: "token", "semantic", "tokenizer" 或 "pysbd"
splitter_type: "pysbd"

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
  language: "en"

# PySBDSplitter 参数
pysbd_splitter:
  max_tokens: 1000
  overlap: 100
  language: "en"

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