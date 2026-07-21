"""
VerifPay — RAG Ingestion Pipeline

Reads fraud data from rbi_alerts/ and india_patterns/ directories,
chunks documents using RecursiveCharacterTextSplitter, embeds using
sentence-transformers/all-MiniLM-L6-v2, and stores in ChromaDB.
"""

import json
import logging
from pathlib import Path
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)


def load_json_documents(directory: Path) -> list[dict]:
    """Load all JSON files from a directory and extract text documents."""
    documents = []

    if not directory.exists():
        logger.warning(f"Directory not found: {directory}")
        return documents

    for json_file in directory.glob("*.json"):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            if isinstance(data, list):
                for item in data:
                    doc = _extract_document(item, source=json_file.name)
                    if doc:
                        documents.append(doc)
            elif isinstance(data, dict):
                doc = _extract_document(data, source=json_file.name)
                if doc:
                    documents.append(doc)

            logger.info(f"Loaded {json_file.name}: {len(data) if isinstance(data, list) else 1} entries")

        except Exception as e:
            logger.error(f"Failed to load {json_file}: {e}")

    return documents


def load_text_documents(directory: Path) -> list[dict]:
    """Load all .txt files from a directory."""
    documents = []

    if not directory.exists():
        logger.warning(f"Directory not found: {directory}")
        return documents

    for txt_file in directory.glob("*.txt"):
        try:
            content = txt_file.read_text(encoding="utf-8").strip()
            if content:
                documents.append({
                    "content": content,
                    "metadata": {
                        "source": txt_file.name,
                        "fraud_type": "UNKNOWN",
                    }
                })
                logger.info(f"Loaded text file: {txt_file.name}")
        except Exception as e:
            logger.error(f"Failed to load {txt_file}: {e}")

    return documents


def _extract_document(item: dict, source: str) -> Optional[dict]:
    """Extract text content and metadata from a JSON entry."""
    # Build the text content from available fields
    parts = []

    if "title" in item:
        parts.append(f"Title: {item['title']}")
    if "pattern" in item:
        parts.append(f"Pattern: {item['pattern']}")
    if "content" in item:
        parts.append(item["content"])
    if "description" in item:
        parts.append(f"Description: {item['description']}")
    if "red_flags" in item and isinstance(item["red_flags"], list):
        parts.append(f"Red flags: {', '.join(item['red_flags'])}")
    if "examples" in item and isinstance(item["examples"], list):
        parts.append(f"Examples: {' | '.join(item['examples'])}")

    content = "\n".join(parts)
    if not content.strip():
        return None

    fraud_type = item.get("fraud_type", "UNKNOWN")

    return {
        "content": content,
        "metadata": {
            "source": source,
            "fraud_type": fraud_type,
        }
    }


def chunk_documents(documents: list[dict], chunk_size: int = 500, chunk_overlap: int = 50) -> list[dict]:
    """Split documents into smaller chunks for embedding."""
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", ". ", ", ", " ", ""],
    )

    chunked = []
    for doc in documents:
        text = doc["content"]
        metadata = doc["metadata"]

        chunks = splitter.split_text(text)
        for i, chunk in enumerate(chunks):
            chunked.append({
                "content": chunk,
                "metadata": {
                    **metadata,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                }
            })

    return chunked


def ingest_to_chroma(persist_dir: str = None):
    """
    Main ingestion pipeline:
    1. Load documents from rbi_alerts/ and india_patterns/
    2. Chunk them
    3. Embed using sentence-transformers
    4. Store in ChromaDB
    """
    import chromadb
    from chromadb.utils import embedding_functions

    persist_dir = persist_dir or settings.CHROMA_PERSIST_DIR

    logger.info("=" * 50)
    logger.info("  VerifPay RAG Ingestion Pipeline")
    logger.info("=" * 50)

    # 1. Load all documents
    all_documents = []

    # Load from rbi_alerts/
    rbi_docs = load_json_documents(settings.RBI_ALERTS_DIR)
    rbi_txt = load_text_documents(settings.RBI_ALERTS_DIR)
    all_documents.extend(rbi_docs)
    all_documents.extend(rbi_txt)
    logger.info(f"RBI alerts loaded: {len(rbi_docs) + len(rbi_txt)} documents")

    # Load from india_patterns/
    pattern_docs = load_json_documents(settings.INDIA_PATTERNS_DIR)
    pattern_txt = load_text_documents(settings.INDIA_PATTERNS_DIR)
    all_documents.extend(pattern_docs)
    all_documents.extend(pattern_txt)
    logger.info(f"India patterns loaded: {len(pattern_docs) + len(pattern_txt)} documents")

    if not all_documents:
        logger.error("No documents found to ingest!")
        return False

    logger.info(f"Total documents loaded: {len(all_documents)}")

    # 2. Chunk documents
    chunks = chunk_documents(all_documents, chunk_size=500, chunk_overlap=50)
    logger.info(f"Total chunks after splitting: {len(chunks)}")

    # 3. Set up ChromaDB with sentence-transformers embeddings
    sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )

    client = chromadb.PersistentClient(path=persist_dir)

    # Delete existing collection if it exists (fresh ingest)
    try:
        client.delete_collection("fraud_patterns")
        logger.info("Deleted existing fraud_patterns collection")
    except Exception:
        pass

    collection = client.create_collection(
        name="fraud_patterns",
        embedding_function=sentence_transformer_ef,
        metadata={"description": "VerifPay fraud pattern knowledge base"},
    )

    # 4. Add documents to collection
    ids = [f"doc_{i}" for i in range(len(chunks))]
    documents = [chunk["content"] for chunk in chunks]
    metadatas = [chunk["metadata"] for chunk in chunks]

    # ChromaDB has a batch size limit, add in batches of 100
    batch_size = 100
    for i in range(0, len(ids), batch_size):
        end = min(i + batch_size, len(ids))
        collection.add(
            ids=ids[i:end],
            documents=documents[i:end],
            metadatas=metadatas[i:end],
        )
        logger.info(f"Added batch {i // batch_size + 1}: {end - i} chunks")

    logger.info(f"Ingestion complete! {collection.count()} chunks in ChromaDB at {persist_dir}")
    return True


if __name__ == "__main__":
    # Run as standalone script for initial ingestion
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    success = ingest_to_chroma()
    if success:
        print("\nRAG ingestion complete!")
    else:
        print("\nRAG ingestion failed!")
        sys.exit(1)
