from io import BytesIO
from pathlib import Path

def load_uploaded_document(filename, content):
    ext=Path(filename).suffix.lower()
    text=""
    if ext==".pdf":
        try:
            from pypdf import PdfReader
            reader=PdfReader(BytesIO(content))
            pages=[]
            for i,page in enumerate(reader.pages):
                pages.append(f"[Page {i+1}] {page.extract_text() or ''}")
            text="\n".join(pages)
        except Exception as e: raise ValueError(f"PDF reading failed: {e}")
    elif ext==".docx":
        try:
            from docx import Document
            doc=Document(BytesIO(content))
            text="\n".join(p.text for p in doc.paragraphs)
            for table in doc.tables:
                for row in table.rows: text += "\n" + " | ".join(c.text for c in row.cells)
        except Exception as e: raise ValueError(f"DOCX reading failed: {e}")
    elif ext==".txt":
        text=content.decode("utf-8",errors="replace")
    else:
        raise ValueError("Unsupported file type. Use PDF, DOCX or TXT.")
    if not text.strip(): raise ValueError("No extractable text found in this document.")
    return [{"text":text,"metadata":{"filename":filename,"page":"document"}}]
