from pathlib import Path
import hashlib
from config import KNOWLEDGE_DIR, TOP_K, MAX_HISTORY_MESSAGES
from ollama_client import OllamaClient
from vector_store import VectorStore
from text_splitter import split_text
from knowledge_graph import KnowledgeGraph

SYSTEM_PROMPT = """You are IntelliDB AI, a friendly and precise Database Management Systems tutor.
Answer in clear, structured language. Use examples and SQL code when useful.
Use retrieved document passages and knowledge-graph triples as supporting context.
Distinguish curated DBMS ontology facts from facts extracted from uploaded documents.
Never claim a graph triple came from an uploaded document unless its source says so.
If retrieved context is insufficient, say so and clearly distinguish general DBMS knowledge.
For SQL, explain the query and mention assumptions about table and column names.
Be concise but educational."""

class RAGPipeline:
    def __init__(self, client=None, store=None):
        self.client = client or OllamaClient()
        self.store = store or VectorStore()
        self.graph = KnowledgeGraph()

    def ingest(self, documents, source_name):
        total = 0
        for doc in documents:
            chunks = split_text(doc["text"])
            if not chunks:
                continue
            embeddings = self.client.embed(chunks)
            ids = [
                hashlib.sha256(f"{source_name}:{i}:{chunk}".encode()).hexdigest()
                for i, chunk in enumerate(chunks)
            ]
            metadatas = [
                {**doc.get("metadata", {}), "source": source_name, "chunk": i}
                for i in range(len(chunks))
            ]
            self.store.add(ids, chunks, embeddings, metadatas)
            self.graph.add_document(chunks, source_name)
            total += len(chunks)
        return total

    def ingest_knowledge_base(self):
        KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
        total = 0
        for path in KNOWLEDGE_DIR.glob("*.md"):
            docs = [{"text": path.read_text(encoding="utf-8"),
                     "metadata": {"filename": path.name}}]
            total += self.ingest(docs, path.name)
        return total

    def retrieve(self, question):
        query_embedding = self.client.embed([question])[0]
        return self.store.search(query_embedding, TOP_K)

    def answer(self, question, history=None):
        hits = self.retrieve(question)
        graph_facts = self.graph.search(question)
        graph_lines = []
        for fact in graph_facts:
            subject = self.graph.entity_label(fact["subject"])
            obj = self.graph.entity_label(fact["object"])
            origin = ", ".join(fact["sources"])
            graph_lines.append(
                f"({subject}) -[{fact['predicate']}]-> ({obj}) "
                f"[source: {origin}; confidence: {fact['confidence']:.2f}]"
            )
        graph_context = "\n".join(graph_lines)
        document_context = "\n\n".join(
            f"[Source: {h['metadata'].get('source', h['metadata'].get('filename', 'Knowledge base'))}]\n{h['text']}"
            for h in hits
        )

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        if document_context:
            messages.append({"role": "system",
                             "content": "Retrieved document passages:\n" + document_context})
        if graph_context:
            messages.append({"role": "system",
                             "content": "Retrieved knowledge-graph triples:\n" + graph_context})
        for item in (history or [])[-MAX_HISTORY_MESSAGES:]:
            if item.get("role") in ("user", "assistant"):
                messages.append({"role": item["role"], "content": item["content"]})
        messages.append({"role": "user", "content": question})

        answer = self.client.chat(messages)
        sources = []
        for hit in hits:
            name = hit["metadata"].get("source") or hit["metadata"].get("filename") or "Knowledge base"
            if name not in sources:
                sources.append(name)
        return {
            "answer": answer,
            "sources": sources,
            "retrieved_chunks": len(hits),
            "graph_facts": graph_facts,
        }
