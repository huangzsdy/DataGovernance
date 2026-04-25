#!/bin/bash

# TextSplit Processor Runner
# ============================
# 方案1: 同步运行（无需Redis/Celery）
#   bash run.sh                        # 默认使用 LangChain TokenTextSplitter
#   bash run.sh --splitter token       # 使用 LangChain TokenTextSplitter
#   bash run.sh --splitter semantic    # 使用 SemanticTextSplitter
#   bash run.sh --splitter tokenizer   # 使用 HuggingFaceTokenizerSplitter
#   bash run.sh --splitter pysbd       # 使用 PySBDSplitter (推荐，按句子精确切分)
#
# 方案2: 并行运行（多进程）
#   bash run.sh --workers 4 --splitter pysbd   # 使用 4 个进程并行处理多个文件
#
# 方案3: 使用Celery异步运行（需要Redis）
#   bash run.sh --celery --splitter pysbd

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --celery)
            CELERY_MODE=true
            shift
            ;;
        --workers)
            MAX_WORKERS="$2"
            shift 2
            ;;
        --splitter)
            SPLITTER_TYPE="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: bash run.sh [--celery] [--workers N] [--splitter token|semantic|tokenizer|pysbd]"
            exit 1
            ;;
    esac
done



# 判断运行模式
if [ "$CELERY_MODE" = true ]; then
    echo "Running with Celery (requires Redis)..."

    # 启动Celery worker（后台）
    celery -A src.celery_app worker --loglevel=info &
    CELERY_PID=$!

    # 等待worker启动
    sleep 3

    # 提交任务
    python -m src.main --config config/settings.yaml

    # 等待用户Ctrl+C或手动停止
    echo "Celery worker running (PID: $CELERY_PID). Press Ctrl+C to stop."
    wait $CELERY_PID
else
    # 同步运行（无需Celery）
    python -m src.main --config config/settings.yaml --sync
fi