import requests
from config import OLLAMA_BASE_URL, OLLAMA_CHAT_MODEL, OLLAMA_EMBED_MODEL, TEMPERATURE

class OllamaError(RuntimeError):
    pass

class OllamaClient:
    def __init__(self, base_url=OLLAMA_BASE_URL, chat_model=OLLAMA_CHAT_MODEL, embed_model=OLLAMA_EMBED_MODEL):
        self.base_url = base_url.rstrip("/")
        self.chat_model = chat_model
        self.embed_model = embed_model
        self.session = requests.Session()

    def _post(self, endpoint, payload, timeout=180):
        try:
            response = self.session.post(f"{self.base_url}{endpoint}", json=payload, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            raise OllamaError(f"Could not reach Ollama at {self.base_url}. Start Ollama and pull the required models. Details: {exc}") from exc

    def chat(self, messages, temperature=TEMPERATURE):
        data = self._post("/api/chat", {
            "model": self.chat_model, "messages": messages, "stream": False,
            "options": {"temperature": temperature}
        })
        return data.get("message", {}).get("content", "").strip()

    def embed(self, texts):
        vectors = []
        for text in texts:
            data = self._post("/api/embed", {"model": self.embed_model, "input": text}, timeout=120)
            emb = data.get("embeddings", [])
            if not emb:
                raise OllamaError("Ollama returned no embedding. Check the Nomic model name and version.")
            vectors.append(emb[0])
        return vectors

    def health(self):
        try:
            r = self.session.get(f"{self.base_url}/api/tags", timeout=4)
            r.raise_for_status()
            names = [m.get("name","") for m in r.json().get("models",[])]
            return {"ok":True,"models":names}
        except Exception as exc:
            return {"ok":False,"error":str(exc),"models":[]}
