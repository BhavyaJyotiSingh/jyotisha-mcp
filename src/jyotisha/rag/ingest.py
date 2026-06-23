"""
RAG Ingestion Utility

Reads text files containing classical scriptures (like BPHS),
chunks them into verses, and stores them in the local ChromaDB vector store.
"""

from pathlib import Path
import json

from jyotisha.rag.retriever import JyotishaRetriever

class TextIngester:
    
    def __init__(self):
        self.retriever = JyotishaRetriever()
        
    def ingest_jsonl(self, file_path: str):
        """
        Ingest a JSONL file containing astrological verses.
        Expected format per line:
        {"id": "bphs_1_1", "text": "The verse translation...", "source": "BPHS", "chapter": 1, "verse": 1, "topic": "creation"}
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
            
        documents = []
        metadatas = []
        ids = []
        
        print(f"Reading {file_path}...")
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    doc_id = data.get("id", f"{data.get('source')}_{data.get('chapter')}_{data.get('verse')}")
                    
                    documents.append(data["text"])
                    ids.append(doc_id)
                    
                    # Store all other keys as metadata
                    meta = {k: v for k, v in data.items() if k not in ["id", "text"]}
                    metadatas.append(meta)
                    
                except json.JSONDecodeError:
                    print(f"Warning: Skipping invalid JSON line: {line[:50]}...")
                    
        if documents:
            print(f"Upserting {len(documents)} documents to ChromaDB...")
            # We chunk the upsert because Chroma has a batch limit (usually ~5000, we'll use 1000)
            batch_size = 1000
            for i in range(0, len(documents), batch_size):
                self.retriever.collection.upsert(
                    documents=documents[i:i+batch_size],
                    metadatas=metadatas[i:i+batch_size],
                    ids=ids[i:i+batch_size]
                )
            print(f"Successfully ingested {len(documents)} verses.")
            print(f"Total documents in DB: {self.retriever.get_collection_stats()['count']}")
        else:
            print("No valid documents found to ingest.")

if __name__ == "__main__":
    # Example usage:
    # ingester = TextIngester()
    # ingester.ingest_jsonl("data/bphs_verses.jsonl")
    pass
