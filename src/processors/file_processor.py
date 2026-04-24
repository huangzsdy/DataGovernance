import json
from pathlib import Path
from typing import List, Dict, Any
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing as mp
from src.processors.text_splitter import create_splitter
from src.utils.logger import logger


def _process_single_file_worker(args):
    """Worker function for multiprocessing"""
    input_file, output_file, config = args
    from src.processors.file_processor import FileProcessor
    processor = FileProcessor(config)
    return processor.process_file(input_file, output_file)


class FileProcessor:
    """File processor for handling JSON/JSONL file processing"""

    def __init__(self, config: dict):
        self.config = config
        self.content_field = config.get("content_field", "content")
        splitter_type = config.get("splitter_type", "token")
        self.splitter = create_splitter(splitter_type, config)
        logger.info(f"FileProcessor initialized with content_field='{self.content_field}', splitter_type='{splitter_type}'")

    def process_line(self, line: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Process a single JSON line, splitting the content field.

        Args:
            line: Dictionary containing the JSON object

        Returns:
            List of dictionaries, each with split_content added
        """
        if self.content_field not in line:
            logger.warning(f"Content field '{self.content_field}' not found in line: {line}")
            return [line]

        content = line.get(self.content_field, "")
        if not content:
            logger.warning(f"Empty content in field '{self.content_field}'")
            return [line]

        # Split the content
        split_contents = self.splitter.split_text(content)
        logger.debug(f"Split content into {len(split_contents)} chunks")

        # Create new JSON objects, each with a split_content field
        result = []
        for split_content in split_contents:
            new_line = line.copy()
            new_line["split_content"] = split_content
            result.append(new_line)

        return result

    def process_lines_batch(self, lines: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process multiple JSON lines in batch for better performance.

        Args:
            lines: List of dictionaries containing JSON objects

        Returns:
            List of dictionaries with split_content added
        """
        if not lines:
            return []

        # Filter lines with valid content
        valid_lines = []
        valid_contents = []
        valid_indices = []

        for i, line in enumerate(lines):
            if self.content_field in line and line.get(self.content_field):
                valid_lines.append(line)
                valid_contents.append(line[self.content_field])
                valid_indices.append(i)

        if not valid_contents:
            return lines

        # Batch split all contents at once
        all_splits = self.splitter.split_texts_batch(valid_contents)

        # Build results
        results = []
        for idx, line in zip(valid_indices, valid_lines):
            splits = all_splits[idx] if idx < len(all_splits) else []
            for split_content in splits:
                new_line = line.copy()
                new_line["split_content"] = split_content
                results.append(new_line)

        # Add lines without content as-is
        for i, line in enumerate(lines):
            if i not in valid_indices:
                results.append(line)

        return results

        # Split the content
        split_contents = self.splitter.split_text(content)
        logger.debug(f"Split content into {len(split_contents)} chunks")

        # Create new JSON objects, each with a split_content field
        result = []
        for split_content in split_contents:
            new_line = line.copy()
            new_line["split_content"] = split_content
            result.append(new_line)

        return result

    def process_file(self, input_path: str, output_path: str) -> dict:
        """
        Process a single JSON/JSONL file.

        Args:
            input_path: Input file path
            output_path: Output file path

        Returns:
            Processing result statistics
        """
        input_path = Path(input_path)
        output_path = Path(output_path)

        # Validate input file
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")

        # Create output directory if needed
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Determine file type
        is_json = input_path.suffix.lower() == ".json"
        is_jsonl = input_path.suffix.lower() == ".jsonl"

        if not is_json and not is_jsonl:
            raise ValueError(f"Unsupported file type: {input_path.suffix}. Must be .json or .jsonl")

        logger.info(f"Reading from {input_path}")

        # Process based on file type
        if is_json:
            return self._process_json_file(input_path, output_path)
        else:
            return self._process_jsonl_file(input_path, output_path)

    def _process_json_file(self, input_path: Path, output_path: Path) -> dict:
        """Process a JSON file (array of objects)"""
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if not isinstance(data, list):
            # Single object, wrap in list
            data = [data]

        output_lines = []
        for line in data:
            processed = self.process_line(line)
            output_lines.extend(processed)

        # Write output
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_lines, f, ensure_ascii=False, indent=2)

        return {
            "input_file": str(input_path),
            "output_file": str(output_path),
            "input_count": len(data),
            "output_count": len(output_lines)
        }

    def _process_jsonl_file(self, input_path: Path, output_path: Path) -> dict:
        """Process a JSONL file (one JSON object per line) with batch optimization"""
        # Read all lines at once
        with open(input_path, 'r', encoding='utf-8') as f:
            lines = [line.strip() for line in f if line.strip()]

        # Parse all JSON at once
        data_list = []
        for line_num, line in enumerate(lines, 1):
            try:
                data_list.append(json.loads(line))
            except json.JSONDecodeError as e:
                logger.warning(f"Skipping invalid JSON at line {line_num}: {e}")

        input_count = len(data_list)

        # Batch process all lines (more efficient)
        output_lines = []
        for data in data_list:
            processed = self.process_line(data)
            output_lines.extend(processed)

        # Write all at once (faster than line by line)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(json.dumps(line, ensure_ascii=False) for line in output_lines))

        return {
            "input_file": str(input_path),
            "output_file": str(output_path),
            "input_count": input_count,
            "output_count": len(output_lines)
        }

    def process_directory(self, input_dir: str, output_dir: str) -> dict:
        """
        Process all JSON/JSONL files in a directory recursively.

        Args:
            input_dir: Input directory path
            output_dir: Output directory path

        Returns:
            Processing results for all files
        """
        input_dir = Path(input_dir)
        output_dir = Path(output_dir)

        if not input_dir.exists():
            raise FileNotFoundError(f"Input directory not found: {input_dir}")

        if not input_dir.is_dir():
            raise ValueError(f"Input path is not a directory: {input_dir}")

        # Find all JSON and JSONL files
        json_files = list(input_dir.rglob("*.json"))
        jsonl_files = list(input_dir.rglob("*.jsonl"))
        all_files = json_files + jsonl_files

        if not all_files:
            logger.warning(f"No JSON/JSONL files found in {input_dir}")
            return {"files_processed": 0, "results": []}

        logger.info(f"Found {len(all_files)} files to process")

        results = []
        for input_file in all_files:
            # Calculate relative path
            relative_path = input_file.relative_to(input_dir)

            # Create output file path with _textSplit suffix
            output_file = self._get_output_path(relative_path, output_dir)

            try:
                result = self.process_file(str(input_file), str(output_file))
                results.append(result)
                logger.info(f"Processed: {input_file} -> {output_file}")
            except Exception as e:
                logger.error(f"Error processing {input_file}: {e}")
                results.append({
                    "input_file": str(input_file),
                    "error": str(e)
                })

        return {
            "files_processed": len(results),
            "results": results
        }

    def process_directory_parallel(self, input_dir: str, output_dir: str, max_workers: int = None) -> dict:
        """
        Process all JSON/JSONL files in a directory in parallel using multiprocessing.

        Args:
            input_dir: Input directory path
            output_dir: Output directory path
            max_workers: Maximum number of worker processes (default: CPU count)

        Returns:
            Processing results for all files
        """
        input_dir = Path(input_dir)
        output_dir = Path(output_dir)

        if not input_dir.exists():
            raise FileNotFoundError(f"Input directory not found: {input_dir}")

        # Find all JSON and JSONL files
        json_files = list(input_dir.rglob("*.json"))
        jsonl_files = list(input_dir.rglob("*.jsonl"))
        all_files = json_files + jsonl_files

        if not all_files:
            logger.warning(f"No JSON/JSONL files found in {input_dir}")
            return {"files_processed": 0, "results": []}

        logger.info(f"Found {len(all_files)} files to process")

        # Prepare task arguments
        tasks = []
        for input_file in all_files:
            relative_path = input_file.relative_to(input_dir)
            output_file = self._get_output_path(relative_path, output_dir)
            tasks.append((str(input_file), str(output_file), self.config))

        # Determine number of workers
        if max_workers is None:
            max_workers = mp.cpu_count()
        logger.info(f"Processing with {max_workers} workers")

        # Process in parallel
        results = []
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(_process_single_file_worker, task): task[0]
                for task in tasks
            }

            for future in as_completed(futures):
                input_file = futures[future]
                try:
                    result = future.result()
                    results.append(result)
                    logger.info(f"Completed: {input_file}")
                except Exception as e:
                    logger.error(f"Error processing {input_file}: {e}")
                    results.append({
                        "input_file": input_file,
                        "error": str(e)
                    })

        return {
            "files_processed": len(results),
            "results": results
        }

    def _get_output_path(self, relative_path: Path, output_dir: Path) -> Path:
        """
        Get output path with _textSplit suffix.

        Example: input.jsonl -> input_textSplit.jsonl
                 subdir/data.json -> subdir/data_textSplit.json

        Args:
            relative_path: Relative path of input file
            output_dir: Output directory

        Returns:
            Output file path
        """
        # Get filename without extension
        stem = relative_path.stem
        suffix = relative_path.suffix

        # Create new filename: stem + _textSplit + suffix
        new_stem = f"{stem}_textSplit"
        new_filename = f"{new_stem}{suffix}"

        return output_dir / relative_path.parent / new_filename