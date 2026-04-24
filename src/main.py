#!/usr/bin/env python
"""
TextSplit Processor - Main Entry Point

Usage:
    # Start Celery worker
    celery -A src.celery_app worker --loglevel=info

    # Run tasks (from Python)
    from src.main import run_single_file, run_directory

    # Or use the CLI
    python -m src.main --config config/settings.yaml
"""

import argparse
import sys
import yaml, os
from pathlib import Path

# Disable transformers warnings
os.environ["TRANSFORMERS_VERBOSITY"] = "error"
os.environ["TOKENIZERS_PARALLELISM"] = "true"

from src.tasks import process_single_file, process_directory
from src.utils.logger import logger

# from huggingface_hub import configure_huggingface_hub

# configure_huggingface_hub(cache_dir="/mnt/c/Users/ThinkPad/Downloads/huggingface/hub")
custom_cache_path = "/mnt/c/Users/ThinkPad/Downloads/huggingface/hub" # 例如: "/data/hf_cache"

# 2. 设置环境变量（旧版本库认这个）
os.environ["HF_HOME"] = custom_cache_path
os.environ["TRANSFORMERS_CACHE"] = custom_cache_path

# 在导入 transformers 前调用
def load_config(config_path: str) -> dict:
    """Load configuration from YAML file"""
    config_path = Path(config_path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    return config


def run_single_file(config_path: str = "config/settings.yaml") -> dict:
    """Run single file processing task"""
    config = load_config(config_path)

    # Override mode to single
    config['mode'] = 'single'

    input_path = config.get('input_path')
    output_path = config.get('output_path')

    if not input_path or not output_path:
        raise ValueError("input_path and output_path must be specified in config")

    logger.info(f"Starting single file processing: {input_path} -> {output_path}")

    # Submit Celery task
    task = process_single_file.delay(input_path, output_path, config)
    logger.info(f"Task submitted: {task.id}")

    return {"task_id": task.id, "status": "submitted"}


def run_directory(config_path: str = "config/settings.yaml") -> dict:
    """Run directory processing task"""
    config = load_config(config_path)

    # Override mode to directory
    config['mode'] = 'directory'

    input_path = config.get('input_path')
    output_path = config.get('output_path')

    if not input_path or not output_path:
        raise ValueError("input_path and output_path must be specified in config")

    logger.info(f"Starting directory processing: {input_path} -> {output_path}")

    # Submit Celery task
    task = process_directory.delay(input_path, output_path, config)
    logger.info(f"Task submitted: {task.id}")

    return {"task_id": task.id, "status": "submitted"}


def run_sync(config_path: str = "config/settings.yaml") -> dict:
    """Run processing synchronously (for testing without Celery)"""
    from src.processors.file_processor import FileProcessor

    config = load_config(config_path)
    processor = FileProcessor(config)

    mode = config.get('mode', 'single')
    input_path = config.get('input_path')
    output_path = config.get('output_path')

    if mode == 'directory':
        # Check if parallel mode is enabled
        max_workers = config.get('max_workers')
        if max_workers and max_workers > 1:
            result = processor.process_directory_parallel(input_path, output_path, max_workers)
        else:
            result = processor.process_directory(input_path, output_path)
    else:
        result = processor.process_file(input_path, output_path)

    logger.info(f"Processing completed: {result}")
    return result


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(description='TextSplit Processor')
    parser.add_argument('--config', '-c', default='config/settings.yaml',
                        help='Path to configuration file')
    parser.add_argument('--mode', '-m', choices=['single', 'directory', 'sync'],
                        help='Processing mode (overrides config)')
    parser.add_argument('--sync', '-s', action='store_true',
                        help='Run synchronously without Celery')

    args = parser.parse_args()

    try:
        config = load_config(args.config)
        mode = args.mode or config.get('mode', 'single')

        if args.sync or mode == 'sync':
            result = run_sync(args.config)
            print(f"Result: {result}")
        elif mode == 'directory':
            result = run_directory(args.config)
            print(f"Task submitted: {result}")
        else:
            result = run_single_file(args.config)
            print(f"Task submitted: {result}")

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()