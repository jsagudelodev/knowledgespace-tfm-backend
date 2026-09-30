# Documentos Válidos para Tutoriales

Estos documentos **tienen archivos reales en S3** y funcionan con los tutoriales.

## Para Tutorial 1 (Embeddings)
```python
DOCUMENT_ID = 37  # Resumen de Clase 1 - Tema 3.pdf (150 KB, 2 páginas, 6 chunks)
```
✓ Mediano, bueno para aprender
- Descarga rápida
- Chunks claros y variados
- Embeddings limpios

**Alternativas:**
- `DOCUMENT_ID = 38` (Resumen Clase 2 - Tema 3.pdf, 121 KB)

---

## Para Tutorial 2 (Pinecone Search)
Usa el mismo documento o alguno de estos:

```python
ASSISTANT_ID = 2  # VCD
DOCUMENT_ID = 37
QUERY = "¿Qué es NLP?"  # Pregunta sobre el contenido del documento
```

**Documentos disponibles:**
- #37: Resumen Clase 1 - Tema 3.pdf (150 KB) ✓
- #36: Diapositivas Tema 2 Clase 3.pdf (1.7 MB) ✓
- #38: Resumen Clase 2 - Tema 3.pdf (121 KB) ✓
- #39: Clase 2 – Modelos Autoregresivos... (2.9 MB) ✓
- #40: Clase 3 – Difusión, LLMs... (4.8 MB) ✓
- #41: Resumen Tema 4 Clase 5.pdf (320 KB) ✓
- #42: Diapositivas Tema 6 - Sesión 1.pdf (1.9 MB) ✓

---

## Para Tutorial 3 (RAG Completo)
```python
ASSISTANT_ID = 2  # VCD
QUERY = "¿Cuál es el objetivo principal de la clase?"
```

Cualquiera de los documentos de arriba.

⚠️ **AVISO**: Este tutorial llama a OpenAI. Costo típico: **$0.0001-$0.0005 por pregunta**

---

## Para Tutorial 4 (Alucinaciones)
Sin dependencias. Corre directamente:
```bash
python docs/tutorials/04_alucinaciones.py
```

---

## Documentos que NO funcionan (rutas rotas en S3):
- #30, #32, #31, #28, #29

Estos tienen rutas antiguas en la BD. Se pueden ignorar o limpiar la BD.

---

## Cómo verificar si un documento tiene archivo

```bash
cd api
python << 'EOF'
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "api"))
sys.path.insert(0, os.getcwd())

from app.core.database import SessionLocal
from app.services.s3_service import S3Service

db = SessionLocal()
s3 = S3Service()
doc_id = 37

doc = db.query(Document).filter(Document.id == doc_id).first()
try:
    s3.descargar_a_memoria(doc.file_path)
    print(f"✓ Documento #{doc_id}: OK")
except:
    print(f"✗ Documento #{doc_id}: NO existe en S3")
db.close()
EOF
```
