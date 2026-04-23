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
# 方案2: 使用Celery异步运行（需要Redis）
#   bash run.sh --celery --splitter pysbd

# 设置新的输入输出目录
INPUT_DIR="/mnt/c/Users/ThinkPad/my_own_files/work/projects/shujupingtai/multi-language/nemotron/test_data"
OUTPUT_DIR="/mnt/c/Users/ThinkPad/my_own_files/work/projects/shujupingtai/multi-language/nemotron/test_data_output"

# 默认splitter类型
SPLITTER_TYPE="pysbd"

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --celery)
            CELERY_MODE=true
            shift
            ;;
        --splitter)
            SPLITTER_TYPE="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: bash run.sh [--celery] [--splitter token|semantic|tokenizer|pysbd]"
            exit 1
            ;;
    esac
done

# 创建输出目录（如果不存在）
mkdir -p "$OUTPUT_DIR"

# 更新配置文件
sed -i "s|^input_path:.*|input_path: \"$INPUT_DIR\"|" config/settings.yaml
sed -i "s|^output_path:.*|output_path: \"$OUTPUT_DIR\"|" config/settings.yaml
sed -i "s|^mode:.*|mode: \"directory\"|" config/settings.yaml
sed -i "s|^splitter_type:.*|splitter_type: \"$SPLITTER_TYPE\"|" config/settings.yaml

echo "Configuration updated:"
echo "  Input:        $INPUT_DIR"
echo "  Output:       $OUTPUT_DIR"
echo "  Mode:         directory"
echo "  Splitter:     $SPLITTER_TYPE"

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
    echo "Running in sync mode (no Redis/Celery required)..."
    # 同步运行（无需Celery）
    python -m src.main --config config/settings.yaml --sync
fi