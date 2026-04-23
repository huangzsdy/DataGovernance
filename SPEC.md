# TextSplit Celery Project Specification

## 1. Project Overview

- **Project Name**: text_split_processor
- **Type**: Python Celery异步任务处理项目
- **Core Functionality**: 使用LangChain对JSON/JSONL文件中的文本进行智能拆分
- **Target Users**: 需要处理大量文本数据的开发者

## 2. Project Structure

```
text_split_processor/
├── config/
│   └── settings.yaml          # 配置文件
├── src/
│   ├── __init__.py
│   ├── main.py                # 入口文件
│   ├── celery_app.py          # Celery应用配置
│   ├── tasks.py               # Celery任务定义
│   ├── processors/
│   │   ├── __init__.py
│   │   ├── base.py            # 基础处理器
│   │   ├── text_splitter.py   # 文本拆分器
│   │   └── file_processor.py  # 文件处理器
│   └── utils/
│       ├── __init__.py
│       └── logger.py          # 日志工具
├── requirements.txt
└── README.md
```

## 3. Functionality Specification

### 3.1 输入输出模式

#### 模式1：单文件模式
- 配置`input_path`和`output_path`为具体文件路径
- 处理单个JSON/JSONL文件

#### 模式2：目录模式
- 配置`input_path`为目录路径
- 递归处理目录下所有.json和.jsonl文件
- 保持原有目录结构创建输出文件
- 输出文件名规则：`原文件名_textSplit.原后缀`

### 3.2 配置文件参数

```yaml
# 处理模式
mode: "single"  # "single" 或 "directory"

# 文件路径
input_path: "data/input.jsonl"
output_path: "data/output.jsonl"

# 文本拆分器配置
splitter_type: "token"  # "token" 或 "semantic"
content_field: "content"  # 要处理的字段名

# TokenTextSplitter参数
token_splitter:
  max_tokens: 1000
  overlap: 100

# SemanticTextSplitter参数
semantic_splitter:
  chunk_size: 1000
  buffer_size: 1
  add_start_index: false

# Celery配置
celery:
  broker: "redis://localhost:6379/0"
  backend: "redis://localhost:6379/1"
```

### 3.3 处理流程

1. 读取输入JSON/JSONL文件（每行一个JSON对象）
2. 对指定`content_field`字段内容进行文本拆分
3. 拆分结果添加到新字段`split_content`
4. 原JSON的其他key全部保留
5. 一行JSON可能变成多行JSON（每句一个）
6. 按输出路径写入结果

### 3.4 输出格式示例

输入：
```json
{"id": 1, "content": "这是第一句话。这是第二句话。这是第三句话。"}
```

输出（假设拆分成3句）：
```json
{"id": 1, "content": "这是第一句话。这是第二句话。这是第三句话。", "split_content": "这是第一句话。"}
{"id": 1, "content": "这是第一句话。这是第二句话。这是第三句话。", "split_content": "这是第二句话。"}
{"id": 1, "content": "这是第一句话。这是第二句话。这是第三句话。", "split_content": "这是第三句话。"}
```

## 4. Acceptance Criteria

1. ✅ 支持配置文件指定单文件和目录两种输入模式
2. ✅ 支持TokenTextSplitter和SemanticTextSplitter两种拆分器
3. ✅ 拆分参数可在配置文件中指定
4. ✅ 保留原JSON所有字段，新增split_content字段
5. ✅ 输出文件名正确添加_textSplit后缀
6. ✅ 目录模式下保持原有文件结构
7. ✅ 使用Celery异步处理任务
8. ✅ 单元测试覆盖核心功能