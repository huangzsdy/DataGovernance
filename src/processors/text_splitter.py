from typing import List
from abc import ABC, abstractmethod
from langchain_text_splitters import TokenTextSplitter, RecursiveCharacterTextSplitter
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


def create_splitter(splitter_type: str, config: dict) -> BaseTextSplitter:
    """
    Factory function to create the appropriate text splitter based on configuration

    Args:
        splitter_type: "token" or "semantic"
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
    else:
        raise ValueError(f"Unknown splitter_type: {splitter_type}. Must be 'token' or 'semantic'")