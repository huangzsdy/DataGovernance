from typing import List, Optional
from abc import ABC, abstractmethod
from transformers import AutoTokenizer
import pysbd
from src.utils.logger import logger


# Language-specific separator presets
# 重要：分隔符按优先级排序，越靠前优先级越高
# 句子结束符(. ? !)应优先于换行符(\n)，以确保按句子切分
LANGUAGE_SEPARATORS = {
    # Western European languages
    "en": [". ", "? ", "! ", "\n\n", "\n", "; ", ", ", " "],  # English - 句子优先
    "es": [". ", "? ", "! ", "\n\n", "\n", "; ", ", ", " "],  # Spanish
    "fr": [". ", "? ", "! ", "\n\n", "\n", "; ", ", ", " "],  # French
    "de": [". ", "? ", "! ", "\n\n", "\n", "; ", ", ", " "],  # German
    "pt": [". ", "? ", "! ", "\n\n", "\n", "; ", ", ", " "],  # Portuguese
    "it": [". ", "? ", "! ", "\n\n", "\n", "; ", ", ", " "],  # Italian

    # Eastern European languages
    "ru": [". ", "? ", "! ", "\n\n", "\n", "; ", ", ", " "],  # Russian
    "uk": [". ", "? ", "! ", "\n\n", "\n", "; ", ", ", " "],  # Ukrainian
    "pl": [". ", "? ", "! ", "\n\n", "\n", "; ", ", ", " "],  # Polish

    # Middle Eastern languages
    "he": [". ", "? ", "! ", "׃", "\n\n", "\n", ";", ", ", " "],  # Hebrew
    "ar": [". ", "? ", "! ", "؛ ", "، ", "\n\n", "\n", " "],  # Arabic

    # South Asian languages
    "hi": ["।", "?", "!", "\n\n", "\n", "; ", ", ", " "],  # Hindi - 梵文句号优先
    "bn": ["।", "?", "!", "\n\n", "\n", "; ", ", ", " "],  # Bengali
    "ta": [". ", "?", "!", "\n\n", "\n", "; ", ", ", " "],  # Tamil
    "te": [". ", "?", "!", "\n\n", "\n", "; ", ", ", " "],  # Telugu
    "mr": ["।", "?", "!", "\n\n", "\n", "; ", ", ", " "],  # Marathi

    # East Asian languages - 句号优先
    "zh": ["。", "！", "？", "\n\n", "\n", "；", "，", " "],  # Chinese
    "ja": ["。", "！", "？", "\n\n", "\n", "；", "、", " "],  # Japanese
    "ko": [". ", "!", "?", "\n\n", "\n", "; ", ", ", " "],  # Korean

    # Southeast Asian languages
    "th": ["।", "?", "!", "\n\n", "\n", "; ", ", ", " "],  # Thai
    "vi": [". ", "? ", "! ", "\n\n", "\n", "; ", ", ", " "],  # Vietnamese
    "id": [". ", "? ", "! ", "\n\n", "\n", "; ", ", ", " "],  # Indonesian
    "ms": [". ", "? ", "! ", "\n\n", "\n", "; ", ", ", " "],  # Malay

    # African languages
    "sw": [". ", "? ", "! ", "\n\n", "\n", "; ", ", ", " "],  # Swahili

    # Multilingual fallback
    "multi": ["。", "！", "？", "।", ". ", "? ", "! ", "׃", "؛", "،", "\n\n", "\n", ", ", " "],
}

# Recommended HuggingFace tokenizers for different languages
RECOMMENDED_TOKENIZERS = {
    "en": "bert-base-uncased",
    "es": "bert-base-multilingual-cased",  # Use mBERT for Spanish
    "fr": "bert-base-multilingual-cased",
    "de": "bert-base-multilingual-cased",
    "pt": "bert-base-multilingual-cased",
    "it": "bert-base-multilingual-cased",
    "ru": "bert-base-multilingual-cased",
    "uk": "bert-base-multilingual-cased",
    "pl": "bert-base-multilingual-cased",
    "he": "bert-base-hebrew",
    "ar": "asafaya/bert-base-arabic",
    "hi": "ai4bharat/IndicBERT",
    "bn": "ai4bharat/IndicBERT",
    "ta": "ai4bharat/IndicBERT",
    "te": "ai4bharat/IndicBERT",
    "mr": "ai4bharat/IndicBERT",
    "zh": "bert-base-chinese",
    "ja": "bert-base-japanese",
    "ko": "beomi/kcbert-base",
    "th": "bool/boolbert-thai",
    "vi": "bert-base-multilingual-cased",
    "id": "bert-base-multilingual-cased",
    "ms": "bert-base-multilingual-cased",
    "sw": "bert-base-multilingual-cased",
    "multi": "bert-base-multilingual-cased",
}


class BaseTextSplitter(ABC):
    """Base class for text splitters"""

    @abstractmethod
    def split_text(self, text: str) -> List[str]:
        """Split text into chunks"""
        pass

    def split_texts_batch(self, texts: List[str]) -> List[List[str]]:
        """
        Batch split multiple texts. Default implementation calls split_text for each.
        Override this for optimized batch processing.
        """
        if not texts:
            return []
        return [self.split_text(text) for text in texts]


# class TokenTextSplitterProcessor(BaseTextSplitter):
#     """TokenTextSplitter processor using LangChain (DEPRECATED)"""
#
#     def __init__(self, max_tokens: int = 1000, overlap: int = 100):
#         self.splitter = TokenTextSplitter(
#             chunk_size=max_tokens,
#             chunk_overlap=overlap
#         )
#         logger.info(f"Initialized TokenTextSplitter with max_tokens={max_tokens}, overlap={overlap}")
#
#     def split_text(self, text: str) -> List[str]:
#         return self.splitter.split_text(text)
#
#
# class SemanticTextSplitterProcessor(BaseTextSplitter):
#     """
#     SemanticTextSplitter processor using LangChain's RecursiveCharacterTextSplitter (DEPRECATED)
#     """
#
#     def __init__(self, chunk_size: int = 1000, buffer_size: int = 1,
#                  add_start_index: bool = False, separators: List[str] = None):
#         if separators is None:
#             separators = ["\n\n", "\n", "。", "！", "？", ". ", "！", "？", " ", ""]
#
#         self.splitter = RecursiveCharacterTextSplitter(
#             chunk_size=chunk_size,
#             chunk_overlap=buffer_size,
#             length_function=len,
#             separators=separators,
#             add_start_index=add_start_index
#         )
#         logger.info(f"Initialized SemanticTextSplitter with chunk_size={chunk_size}")
#
#     def split_text(self, text: str) -> List[str]:
#         return self.splitter.split_text(text)


class HuggingFaceTokenizerSplitter(BaseTextSplitter):
    """
    Text splitter using HuggingFace tokenizer for accurate token counting.

    This splitter:
    1. Uses a HuggingFace tokenizer to count tokens accurately
    2. Splits text by sentences first (language-specific separators)
    3. Groups sentences into chunks that don't exceed max_tokens
    4. Preserves overlap between chunks for context continuity

    Supports multilingual text with language-specific separators and tokenizers.

    Reference: NVIDIA NeMo Curator's token counting approach
    """

    # Class-level cache for tokenizers and segmenters
    _tokenizer_cache = {}
    _segmenter_cache = {}

    # Language code mapping
    language_map = {
        "zh": "zh", "zh-cn": "zh", "zh-tw": "zh",
        "en": "en", "en-us": "en", "en-gb": "en",
        "es": "es", "fr": "fr", "de": "de", "it": "it",
        "ru": "ru", "pt": "pt", "ja": "ja", "ko": "ko",
        "ar": "ar", "he": "he", "hi": "hi", "bn": "bn",
        "multi": "en",  # multi 语言时使用英文 segmenter 作为 fallback
    }

    def __init__(
        self,
        max_tokens: int = 1000,
        overlap: int = 100,
        hf_model_name: str = "bert-base-uncased",
        language: str = "en",
        separators: Optional[List[str]] = None
    ):
        """
        Args:
            max_tokens: Maximum number of tokens per chunk
            overlap: Number of tokens to overlap between chunks
            hf_model_name: HuggingFace model name for tokenizer
            language: Language code for separator selection (en, es, he, zh, etc.)
            separators: Custom separators list (overrides language preset)
        """
        self.max_tokens = max_tokens
        self.overlap = overlap
        self.language = language.lower()

        # Determine separators: custom > language preset > default
        if separators is not None:
            self.separators = separators
        elif self.language in LANGUAGE_SEPARATORS:
            self.separators = LANGUAGE_SEPARATORS[self.language]
        else:
            logger.warning(f"Language '{self.language}' not found, using default separators")
            self.separators = LANGUAGE_SEPARATORS["multi"]

        # Determine tokenizer: custom > recommended for language > default
        if hf_model_name != "bert-base-uncased":
            self.hf_model_name = hf_model_name
        elif self.language in RECOMMENDED_TOKENIZERS:
            self.hf_model_name = RECOMMENDED_TOKENIZERS[self.language]
        else:
            self.hf_model_name = "bert-base-multilingual-cased"

        # Initialize tokenizer (with caching for efficiency)
        self._init_tokenizer()

        # Initialize pysbd segmenter for sentence splitting
        self._init_segmenter()

        logger.info(f"Initialized HuggingFaceTokenizerSplitter:")
        logger.info(f"  Language: {self.language}")
        logger.info(f"  Tokenizer: {self.hf_model_name}")
        logger.info(f"  Max tokens: {max_tokens}, Overlap: {overlap}")
        logger.info(f"  Separators: {self.separators}")

    def _init_tokenizer(self):
        """Initialize tokenizer with caching"""
        if self.hf_model_name not in HuggingFaceTokenizerSplitter._tokenizer_cache:
            logger.info(f"Loading HuggingFace tokenizer: {self.hf_model_name}")
            HuggingFaceTokenizerSplitter._tokenizer_cache[self.hf_model_name] = \
                AutoTokenizer.from_pretrained(self.hf_model_name)
        self.tokenizer = HuggingFaceTokenizerSplitter._tokenizer_cache[self.hf_model_name]

    def _init_segmenter(self):
        """Initialize pysbd segmenter for sentence splitting"""
        normalized_lang = self.language_map.get(self.language, self.language)
        if normalized_lang not in HuggingFaceTokenizerSplitter._segmenter_cache:
            logger.info(f"Initializing pysbd segmenter for language: {normalized_lang}")
            HuggingFaceTokenizerSplitter._segmenter_cache[normalized_lang] = pysbd.Segmenter(
                language=normalized_lang,
                clean=False
            )
        self.segmenter = HuggingFaceTokenizerSplitter._segmenter_cache[normalized_lang]

    def _split_by_sentences(self, text: str) -> List[str]:
        """Split text into sentences using separators."""
        if not text:
            return []

        # Use pysbd for sentence splitting (replaces RecursiveCharacterTextSplitter)
        sentences = self.segmenter.segment(text)
        return sentences if sentences else []

    def _count_tokens(self, text: str) -> int:
        """Count tokens using the tokenizer."""
        return len(self.tokenizer.encode(text, add_special_tokens=True))

    def _count_tokens_batch(self, texts: List[str]) -> List[int]:
        """
        Count tokens for multiple texts in one batch call (much faster).
        """
        if not texts:
            return []
        # Batch encode all texts at once
        encoded = self.tokenizer(texts, add_special_tokens=True, truncation=False)
        return [len(ids) for ids in encoded['input_ids']]

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


class PySBDSplitter(BaseTextSplitter):
    """
    使用 pysbd (Python Sentence Boundary Detection) 进行多语言句子分割的切分器。

    pysbd 是一个专业的句子边界检测库，支持 60+ 语言。
    特点：
    - 基于语言规则进行精确的句子分割
    - 准确处理缩写、缩写词、书名号等边界情况
    """

    # Class-level cache for segmenters
    _segmenter_cache = {}

    # Language code mapping
    language_map = {
        "zh": "zh", "zh-cn": "zh", "zh-tw": "zh",
        "en": "en", "en-us": "en", "en-gb": "en",
        "es": "es", "fr": "fr", "de": "de", "it": "it",
        "ru": "ru", "pt": "pt", "ja": "ja", "ko": "ko",
        "ar": "ar", "he": "he", "hi": "hi", "bn": "bn",
        "multi": "en",  # multi 语言时使用英文 segmenter 作为 fallback
    }

    def __init__(self, max_tokens: int = 1000, overlap: int = 100, language: str = "en"):
        """
        初始化 PySBDSplitter。

        Args:
            max_tokens: 每个 chunk 的最大 token 数
            overlap: 相邻 chunk 之间的 token 重叠数
            language: 语言代码，例如 'en', 'zh', 'es' 等
        """
        self.max_tokens = max_tokens
        self.overlap = overlap
        self.language = language

        # 获取标准化的语言代码
        normalized_lang = self.language_map.get(language.lower(), language)

        # 初始化 pysbd segmenter（带缓存）
        if normalized_lang not in PySBDSplitter._segmenter_cache:
            logger.info(f"Initializing pysbd segmenter for language: {normalized_lang}")
            PySBDSplitter._segmenter_cache[normalized_lang] = pysbd.Segmenter(
                language=normalized_lang, clean=False
            )
        self.segmenter = PySBDSplitter._segmenter_cache[normalized_lang]

        # 初始化 tokenizer，使用原始 language 参数以支持 multi
        self._init_tokenizer(language)

        logger.info(f"Initialized PySBDSplitter with language={language}, max_tokens={max_tokens}, overlap={overlap}")

    def _init_tokenizer(self, language: str):
        """Initialize tokenizer based on language"""
        if language == "multi":
            # 多语言文本使用 multilingual 模型
            tokenizer_name = "bert-base-multilingual-cased"
        elif language == "zh":
            tokenizer_name = "bert-base-chinese"
        elif language == "ja":
            tokenizer_name = "bert-base-japanese"
        elif language == "ko":
            tokenizer_name = "beomi/kcbert-base"
        elif language == "he":
            tokenizer_name = "bert-base-hebrew"
        elif language == "ar":
            tokenizer_name = "asafaya/bert-base-arabic"
        elif language in ["hi", "bn", "ta", "te", "mr"]:
            tokenizer_name = "ai4bharat/IndicBERT"
        elif language == "en":
            tokenizer_name = "bert-base-uncased"
        else:
            tokenizer_name = "bert-base-multilingual-cased"

        if tokenizer_name not in HuggingFaceTokenizerSplitter._tokenizer_cache:
            HuggingFaceTokenizerSplitter._tokenizer_cache[tokenizer_name] = \
                AutoTokenizer.from_pretrained(tokenizer_name)
        self.tokenizer = HuggingFaceTokenizerSplitter._tokenizer_cache[tokenizer_name]

    def _count_tokens(self, text: str) -> int:
        return len(self.tokenizer.encode(text, add_special_tokens=True))

    def split_text(self, text: str) -> List[str]:
        """
        使用 pysbd 进行句子分割，然后按 token 数合并为 chunks。

        Args:
            text: 待分割的文本

        Returns:
            按 token 限制分割后的文本块列表
        """
        if not text or not isinstance(text, str):
            return []

        # Step 1: 使用 pysbd 进行句子分割
        sentences = self.segmenter.segment(text)

        if not sentences:
            return [text] if text.strip() else []

        # Step 2: 按 token 数合并句子
        chunks = []
        current_chunk = []
        current_tokens = 0

        for sentence in sentences:
            sentence_tokens = self._count_tokens(sentence)

            # 如果单个句子超过 max_tokens，进一步按字符切分
            if sentence_tokens > self.max_tokens:
                if current_chunk:
                    chunks.append(" ".join(current_chunk))
                    current_chunk = []
                    current_tokens = 0

                # 按字符切分长句
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

            # 检查是否超过 max_tokens
            if current_tokens + sentence_tokens > self.max_tokens and current_chunk:
                chunks.append(" ".join(current_chunk))

                # 处理 overlap
                if self.overlap > 0:
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

            # 添加句子到当前 chunk
            current_chunk.append(sentence)
            current_tokens += sentence_tokens

        # 添加剩余的 chunk
        if current_chunk:
            chunks.append(" ".join(current_chunk))

        # 过滤空 chunk
        return [chunk for chunk in chunks if chunk.strip()]


def create_splitter(splitter_type: str, config: dict) -> BaseTextSplitter:
    """
    Factory function to create the appropriate text splitter based on configuration

    Args:
        splitter_type: "tokenizer" or "pysbd" (token and semantic are deprecated)
        config: Configuration dictionary

    Returns:
        BaseTextSplitter instance
    """
    # if splitter_type == "token":
    #     # DEPRECATED: Use tokenizer or pysbd instead
    #     token_config = config.get("token_splitter", {})
    #     return TokenTextSplitterProcessor(
    #         max_tokens=token_config.get("max_tokens", 1000),
    #         overlap=token_config.get("overlap", 100)
    #     )
    # elif splitter_type == "semantic":
    #     # DEPRECATED: Use tokenizer or pysbd instead
    #     semantic_config = config.get("semantic_splitter", {})
    #     return SemanticTextSplitterProcessor(
    #         chunk_size=semantic_config.get("chunk_size", 1000),
    #         buffer_size=semantic_config.get("buffer_size", 1),
    #         add_start_index=semantic_config.get("add_start_index", False)
    #     )
    if splitter_type == "tokenizer":
        tokenizer_config = config.get("tokenizer_splitter", {})
        return HuggingFaceTokenizerSplitter(
            max_tokens=tokenizer_config.get("max_tokens", 1000),
            overlap=tokenizer_config.get("overlap", 100),
            hf_model_name=tokenizer_config.get("hf_model_name", "bert-base-uncased"),
            language=tokenizer_config.get("language", "en")
        )
    elif splitter_type == "pysbd":
        pysbd_config = config.get("pysbd_splitter", {})
        return PySBDSplitter(
            max_tokens=pysbd_config.get("max_tokens", 1000),
            overlap=pysbd_config.get("overlap", 100),
            language=pysbd_config.get("language", "en")
        )
    else:
        raise ValueError(f"Unknown splitter_type: {splitter_type}. Must be 'tokenizer' or 'pysbd'")