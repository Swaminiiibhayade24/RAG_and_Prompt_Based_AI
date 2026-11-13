import chromadb
from chromadb.config import Settings
from config import CHROMA_DIR, TOP_K

class VectorStore:
    def __init__(self, path=CHROMA_DIR, collection_name="intellidb_knowledge"):
        path.mkdir(parents=True,exist_ok=True)
        self.client=chromadb.PersistentClient(path=str(path),settings=Settings(anonymized_telemetry=False))
        self.collection=self.client.get_or_create_collection(
            name=collection_name, metadata={"hnsw:space":"cosine"}
        )

    def add(self, ids, documents, embeddings, metadatas):
        if documents:
            self.collection.upsert(ids=ids,documents=documents,embeddings=embeddings,metadatas=metadatas)

    def search(self, embedding, top_k=TOP_K):
        if self.collection.count()==0: return []
        result=self.collection.query(query_embeddings=[embedding],n_results=min(top_k,self.collection.count()))
        items=[]
        for i,doc in enumerate(result.get("documents",[[]])[0]):
            meta=(result.get("metadatas",[[]])[0] or [{}])[i]
            distance=(result.get("distances",[[]])[0] or [1])[i]
            items.append({"text":doc,"metadata":meta,"distance":distance})
        return items

    def count(self):
        return self.collection.count()
