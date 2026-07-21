"""
VerifPay — Document Chunking Utilities

Provides text splitting and chunking helpers for the RAG pipeline.
"""

from langchain_text_splitters import RecursiveCharacterTextSplitter


def get_text_splitter(chunk_size: int = 500, chunk_overlap: int = 50) -> RecursiveCharacterTextSplitter:
    """Create a configured text splitter for fraud documents."""
    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", ". ", ", ", " ", ""],
    )
