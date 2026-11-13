# ✦ IntelliDB AI

An AI-powered DBMS learning assistant built with **Python, Streamlit, Ollama (Llama 3.2), Nomic Embed Text and ChromaDB**.

## Features

- Modern dark interface with gradient branding and responsive Streamlit layout
- AI chat with conversation history persisted locally in `data/chat_history.json`
- Ollama chat completion using Llama 3.2
- Semantic document retrieval using Nomic Embed Text + ChromaDB
- Persistent DBMS knowledge graph with concept nodes and typed relationship edges
- Graph-augmented RAG: relevant graph facts are added alongside vector-retrieved chunks
- Interactive Knowledge Graph Explorer built into the Streamlit sidebar
- Upload and index PDF, DOCX and TXT study material
- DBMS learning studio covering fundamentals, keys, normalization, ACID, joins and indexes
- Interactive DBMS multiple-choice quiz
- Source list shown for retrieved document context
- Modular backend: loader, splitter, vector store, Ollama client and RAG pipeline

## Requirements

- Python 3.10 or newer
- Ollama installed and running
- Models downloaded locally:
  - `llama3.2`
  - `nomic-embed-text`

## Installation

### 1. Extract the ZIP and open the folder

```bash
cd IntelliDB_AI
```

### 2. Create a virtual environment

Windows:
```powershell
python -m venv .venv
.venv\Scripts\activate
```

macOS / Linux:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Install and start Ollama

Install Ollama from https://ollama.com/download, then run:

```bash
ollama pull llama3.2
ollama pull nomic-embed-text
ollama serve
```

If Ollama is already running as a background service, you do not need to start it again.

### 5. Run IntelliDB AI

```bash
streamlit run app.py
```

Open the local URL printed by Streamlit, usually http://localhost:8501.

## Add your DBMS knowledge base

Place `.md` files in `knowledge_base/`. For the first indexing, use the Documents page to upload PDF, DOCX or TXT materials. The app stores vectors persistently in `data/chroma/`.

The provided `knowledge_base/DBMS_Quick_Reference.md` is a starter reference. To index markdown files from the knowledge-base directory programmatically:

```bash
python -c "from rag_pipeline import RAGPipeline; print(RAGPipeline().ingest_knowledge_base())"
```

## Configuration

Set environment variables before launch if required:

| Variable | Default | Purpose |
|---|---|---|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server |
| `OLLAMA_CHAT_MODEL` | `llama3.2` | Chat model |
| `OLLAMA_EMBED_MODEL` | `nomic-embed-text` | Embedding model |
| `CHUNK_SIZE` | `850` | Characters per text chunk |
| `CHUNK_OVERLAP` | `140` | Overlap between chunks |
| `TOP_K` | `5` | Retrieved chunks per question |

## Project structure

```text
IntelliDB_AI/
├── app.py
├── config.py
├── ollama_client.py
├── rag_pipeline.py
├── document_loader.py
├── text_splitter.py
├── vector_store.py
├── knowledge_graph.py       # Persistent concept graph + relation extraction
├── prompt_template.py
├── learning_content.py
├── requirements.txt
├── README.md
├── knowledge_base/
│   └── DBMS_Quick_Reference.md
└── data/
    └── .gitkeep
```

## Troubleshooting

- **Ollama connection error:** make sure `ollama serve` is running and `http://localhost:11434` is reachable.
- **Model not found:** run `ollama pull llama3.2` and `ollama pull nomic-embed-text`.
- **Embedding error:** confirm the embedding model is installed and available in `ollama list`.
- **PDF has no text:** scanned PDFs need OCR before they can be indexed.
- **Slow first response:** the first model load and embedding/indexing may take longer on CPU-only machines.

## Privacy

Chat history and ChromaDB vectors are stored locally in the project folder. Uploaded documents are processed locally through your Ollama server. Do not upload confidential documents unless your local machine and Ollama environment are appropriately secured.


## Knowledge graph

IntelliDB now builds a lightweight DBMS knowledge graph whenever documents are indexed.
It recognizes common DBMS concepts (keys, normalization forms, SQL, joins, indexes,
transactions, ACID properties, ER modeling, and more), records their source documents,
and extracts relation phrases such as `REFERENCES`, `DEPENDS_ON`, and `IS_A`.
Concepts appearing in the same sentence are also connected with `RELATED_TO` edges;
these indicate co-occurrence, not a verified semantic relation.

The graph is stored locally in `data/knowledge_graph.json`. The RAG pipeline adds
matching graph facts to the retrieved vector context, and the **Knowledge Graph**
sidebar page visualizes extracted nodes and edges. Index documents again after upgrading
to populate the graph from existing material. The graph extractor is intentionally
lightweight and rule-based; validate extracted relationships against the source text.


## Entity-relation knowledge graph (enhanced)

The graph now uses stable DBMS entity IDs and directed, labeled triples:
`(subject)-[predicate]->(object)`. It ships with a curated DBMS ontology covering
keys, tables, normalization, functional dependencies, SQL, joins, indexes,
transactions, ACID properties, concurrency control, ER modeling, and query
optimization. Example facts include:

- `(table)-[HAS_PRIMARY_KEY]->(primary_key)`
- `(foreign_key)-[REFERENCES]->(primary_key)`
- `(2nf)-[ELIMINATES]->(partial_dependency)`
- `(acid)-[INCLUDES]->(atomicity)`
- `(inner_join)-[IS_A]->(join)`

Uploaded documents are scanned for explicit relation phrases. The extractor only
adds a document triple when it can resolve both ends to known entities; it does
not infer factual edges merely because two concepts occur in the same sentence.
Each extracted triple stores its source and evidence sentence. Built-in ontology
facts are labeled `built_in_dbms_ontology`, so they are distinguishable from
document-derived facts.

The graph is persisted at `data/knowledge_graph.json`. The RAG pipeline retrieves
graph triples for entities mentioned in the question and combines them with
ChromaDB passages before calling Ollama. The Streamlit Knowledge Graph page
visualizes entities and predicate labels. Existing uploaded documents can be
re-uploaded to extract their explicit relations into the graph.
