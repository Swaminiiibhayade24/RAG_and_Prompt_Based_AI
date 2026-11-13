from config import CHUNK_SIZE, CHUNK_OVERLAP

def split_text(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    text = " ".join((text or "").split())
    if not text:
        return []
    chunks=[]
    start=0
    while start < len(text):
        end=min(start+chunk_size,len(text))
        if end < len(text):
            boundary=text.rfind(" ",start+int(chunk_size*.65),end)
            if boundary > start: end=boundary
        chunk=text[start:end].strip()
        if chunk: chunks.append(chunk)
        if end >= len(text): break
        start=max(end-overlap,start+1)
    return chunks
