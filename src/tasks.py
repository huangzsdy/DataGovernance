from pathlib import Path
from src.celery_app import celery_app
from src.processors.file_processor import FileProcessor
from src.utils.logger import logger


@celery_app.task(name='process_single_file')
def process_single_file(input_path: str, output_path: str, config: dict) -> dict:
    """处理单个JSON/JSONL文件"""
    logger.info(f"Processing file: {input_path}")
    try:
        processor = FileProcessor(config)
        result = processor.process_file(input_path, output_path)
        logger.info(f"Completed processing: {input_path}, output: {output_path}")
        return result
    except Exception as e:
        logger.error(f"Error processing file {input_path}: {str(e)}")
        raise


@celery_app.task(name='process_directory')
def process_directory(input_dir: str, output_dir: str, config: dict) -> dict:
    """处理整个目录下的所有JSON/JSONL文件"""
    logger.info(f"Processing directory: {input_dir}")
    try:
        processor = FileProcessor(config)
        result = processor.process_directory(input_dir, output_dir)
        logger.info(f"Completed processing directory: {input_dir}")
        return result
    except Exception as e:
        logger.error(f"Error processing directory {input_dir}: {str(e)}")
        raise