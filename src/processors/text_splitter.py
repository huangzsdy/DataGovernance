from typing import List
from abc import ABC, abstractmethod
from langchain_text_splitters import TokenTextSplitter, RecursiveCharacterTextSplitter
from transformers import AutoTokenizer
from src.utils.logger import logger


class BaseTextSplitter(ABC):
    """Base class for text splitters"""

    @abstractmethod
    def split_text(self, text: str) -> List[str]:
        """Split text into chunks"""
        pass


class TokenTextSplitterProcessor(BaseTextSplitter):
    """TokenTextSplitter processor using LangChain"""

    def __init__(self, max_tokens: int = 1000, overlap: int = 100):
        self.splitter = TokenTextSplitter(
            chunk_size=max_tokens,
            chunk_overlap=overlap
        )
        logger.info(f"Initialized TokenTextSplitter with max_tokens={max_tokens}, overlap={overlap}")

    def split_text(self, text: str) -> List[str]:
        return self.splitter.split_text(text)


class SemanticTextSplitterProcessor(BaseTextSplitter):
    """
    SemanticTextSplitter processor using LangChain's RecursiveCharacterTextSplitter
    with semantic-aware parameters to simulate semantic splitting behavior.

    Note: LangChain 0.3.x uses RecursiveCharacterTextSplitter as the primary semantic splitter.
    For true semantic splitting, you can use the SemanticChunker from langchain-experimental
    or configure RecursiveCharacterTextSplitter with appropriate separators.
    """

    def __init__(self, chunk_size: int = 1000, buffer_size: int = 1,
                 add_start_index: bool = False, separators: List[str] = None):
        if separators is None:
            # Separators ordered by priority for semantic splitting
            separators = ["\n\n", "\n", "。", "！", "？", ". ", "！", "？", " ", ""]

        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=buffer_size,
            length_function=len,
            separators=separators,
            add_start_index=add_start_index
        )
        logger.info(f"Initialized SemanticTextSplitter (RecursiveCharacterTextSplitter) with chunk_size={chunk_size}")

    def split_text(self, text: str) -> List[str]:
        return self.splitter.split_text(text)


class HuggingFaceTokenizerSplitter(BaseTextSplitter):
    """
    Text splitter using HuggingFace tokenizer for accurate token counting.

    This splitter:
    1. Uses a HuggingFace tokenizer to count tokens accurately
    2. Splits text by sentences first
    3. Groups sentences into chunks that don't exceed max_tokens
    4. Preserves overlap between chunks for context continuity

    Reference: NVIDIA NeMo Curator's token counting approach
    """

    def __init__(
        self,
        max_tokens: int = 1000,
        overlap: int = 100,
        hf_model_name: str = "bert-base-uncased",
        separators: List[str] = None
    ):
        """
        Args:
            max_tokens: Maximum number of tokens per chunk
            overlap: Number of tokens to overlap between chunks
            hf_model_name: HuggingFace model name for tokenizer
            separators: List of separators for sentence splitting (ordered by priority)
        """
        self.max_tokens = max_tokens
        self.overlap = overlap

        # Initialize tokenizer
        logger.info(f"Loading HuggingFace tokenizer: {hf_model_name}")
        self.tokenizer = AutoTokenizer.from_pretrained(hf_model_name)

        # Default separators for sentence splitting
        if separators is None:
            separators = ["\n\n", "\n", "。", "！", "？", ". ", "！", "？", " ", ""]

        self.separators = separators
        logger.info(f"Initialized HuggingFaceTokenizerSplitter with max_tokens={max_tokens}, overlap={overlap}, model={hf_model_name}")

    def _split_by_sentences(self, text: str) -> List[str]:
        """Split text into sentences using separators."""
        if not text:
            return []

        # Use RecursiveCharacterTextSplitter for sentence splitting
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=10000,  # Large enough to not split sentences
            chunk_overlap=0,
            length_function=len,
            separators=self.separators
        )
        return splitter.split_text(text)

    def _count_tokens(self, text: str) -> int:
        """Count tokens using the tokenizer."""
        return len(self.tokenizer.encode(text, add_special_tokens=True))

    def split_text(self, text: str) -> List[str]:
        """
        Split text into token-limited chunks.

        Algorithm:
        1. Split text into sentences
        2. Build chunks by adding sentences until max_tokens is reached
        3. Handle overlap by preserving last N tokens from previous chunk
        """
        if not text:
            return []

        # Split into sentences
        sentences = self._split_by_sentences(text)
        if not sentences:
            return [text] if text else []

        chunks = []
        current_chunk = []
        current_tokens = 0

        for sentence in sentences:
            sentence_tokens = self._count_tokens(sentence)

            # If single sentence exceeds max_tokens, split it further
            if sentence_tokens > self.max_tokens:
                # Save current chunk first
                if current_chunk:
                    chunks.append(" ".join(current_chunk))
                    current_chunk = []
                    current_tokens = 0

                # Split long sentence by characters
                chars = list(sentence)
                temp_chunk = []
                temp_tokens = 0

                for char in chars:
                    char_tokens = self._count_tokens(char)
                    if temp_tokens + char_tokens > self.max_tokens:
                        if temp_chunk:
                            chunks.append("".join(temp_chunk))
                        temp_chunk = [char]
                        temp_tokens = char_tokens
                    else:
                        temp_chunk.append(char)
                        temp_tokens += char_tokens

                if temp_chunk:
                    current_chunk = temp_chunk
                    current_tokens = temp_tokens
                continue

            # Check if adding this sentence would exceed max_tokens
            if current_tokens + sentence_tokens > self.max_tokens and current_chunk:
                # Save current chunk
                chunks.append(" ".join(current_chunk))

                # Handle overlap - keep last overlap tokens
                if self.overlap > 0 and len(chunks) > 0:
                    # For simplicity, we'll handle overlap at the sentence level
                    # Take last few sentences that fit in overlap
                    overlap_sentences = []
                    overlap_tokens = 0
                    for s in reversed(current_chunk):
                        s_tokens = self._count_tokens(s)
                        if overlap_tokens + s_tokens <= self.overlap:
                            overlap_sentences.insert(0, s)
                            overlap_tokens += s_tokens
                        else:
                            break

                    current_chunk = overlap_sentences
                    current_tokens = overlap_tokens
                else:
                    current_chunk = []
                    current_tokens = 0

            # Add sentence to current chunk
            current_chunk.append(sentence)
            current_tokens += sentence_tokens

        # Add remaining chunk
        if current_chunk:
            chunks.append(" ".join(current_chunk))

        # Filter out empty chunks
        return [chunk for chunk in chunks if chunk.strip()]


def create_splitter(splitter_type: str, config: dict) -> BaseTextSplitter:
    """
    Factory function to create the appropriate text splitter based on configuration

    Args:
        splitter_type: "token", "semantic", or "tokenizer"
        config: Configuration dictionary

    Returns:
        BaseTextSplitter instance
    """
    if splitter_type == "token":
        token_config = config.get("token_splitter", {})
        return TokenTextSplitterProcessor(
            max_tokens=token_config.get("max_tokens", 1000),
            overlap=token_config.get("overlap", 100)
        )
    elif splitter_type == "semantic":
        semantic_config = config.get("semantic_splitter", {})
        return SemanticTextSplitterProcessor(
            chunk_size=semantic_config.get("chunk_size", 1000),
            buffer_size=semantic_config.get("buffer_size", 1),
            add_start_index=semantic_config.get("add_start_index", False)
        )
    elif splitter_type == "tokenizer":
        tokenizer_config = config.get("tokenizer_splitter", {})
        return HuggingFaceTokenizerSplitter(
            max_tokens=tokenizer_config.get("max_tokens", 1000),
            overlap=tokenizer_config.get("overlap", 100),
            hf_model_name=tokenizer_config.get("hf_model_name", "bert-base-uncased")
        )
    else:
        raise ValueError(f"Unknown splitter_type: {splitter_type}. Must be 'token', 'semantic', or 'tokenizer'")