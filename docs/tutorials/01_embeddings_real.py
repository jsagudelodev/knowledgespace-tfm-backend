#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TUTORIAL 1 (REAL): Embeddings con tus documentos

Este script toma UN DOCUMENTO REAL de tu proyecto, lo divide en chunks,
genera embeddings y te muestra qué sucede en cada paso.

Edita DOCUMENT_ID abajo con el ID de un documento que ya tengas.
Para ver IDs disponibles, corre: 00_explorar_proyecto.py

Ejecutar:
  cd D:\Proyectos\GitHub\Sass\KnowledgeSpace\api
  python ..\docs\tutorials\01_embeddings_real.py
"""
import os
import sys
sys.stdout.reconfigure(encoding='utf-8')
os.chdir(r"D:\Proyectos\GitHub\Sass\KnowledgeSpace\api")
sys.path.insert(0, os.getcwd())

from app.core.database import SessionLocal
from app.db.models.document import Document
from app.services.pdf_service import PDFService
from app.services.embedding_service import EmbeddingService
from app.services.s3_service import S3Service
import traceback

# ─── EDITA ESTO ───────────────────────────────────────────────────────
DOCUMENT_ID = 37  # "Resumen de Clase 1 - Tema 3.pdf" (✓ archivo existe en S3)
# ───────────────────────────────────────────────────────────────────────

db = SessionLocal()

print("=" * 70)
print("TUTORIAL 1: EMBEDDINGS CON TUS DOCUMENTOS REALES")
print("=" * 70)

# Paso 1: Obtener el documento de la BD
print(f"\n1️⃣  Buscando documento #{DOCUMENT_ID} en la BD...")
doc = db.query(Document).filter(Document.id == DOCUMENT_ID).first()

if not doc:
    print(f"   ❌ Documento #{DOCUMENT_ID} no encontrado")
    print(f"   Corre primero: 00_explorar_proyecto.py")
    exit(1)

print(f"   ✓ Encontrado: {doc.original_filename}")
print(f"   Tamaño: {doc.file_size} bytes")
print(f"   Estado: {doc.status if hasattr(doc, 'status') else '?'}")
print(f"   Ruta S3: {doc.file_path}")

# Verificar que el documento esté completado
if hasattr(doc, 'status') and doc.status != 'completed':
    print(f"\n   ⚠️  El documento está en estado '{doc.status}', no 'completed'")
    print(f"   Prueba con otro documento que tenga estado 'completed'")
    exit(1)

# Paso 2: Descargar el archivo desde S3
print(f"\n2️⃣  Descargando {doc.original_filename} desde S3...")
try:
    s3 = S3Service()
    buffer = s3.descargar_a_memoria(doc.file_path)
    print(f"   ✓ Descargado ({len(buffer.getvalue())} bytes en memoria)")
except Exception as e:
    print(f"   ❌ Error descargando de S3: {e}")
    print(f"\n   Posibles causas:")
    print(f"   1. El archivo fue eliminado de S3")
    print(f"   2. El documento nunca se procesó completamente")
    print(f"   3. Credenciales de AWS inválidas en .env")
    print(f"\n   Intenta con otro documento que tenga estado 'completed'")
    print(f"   Corre: python ..\docs\tutorials\00_explorar_proyecto.py")
    exit(1)

# Paso 3: Extraer texto según tipo de archivo
print(f"\n3️⃣  Extrayendo texto del archivo ({doc.mime_type})...")
file_type = doc.filename.split(".")[-1].lower()
try:
    chunks, page_count = PDFService.procesar(doc.file_path, file_type=file_type)
    print(f"   ✓ Extraído:")
    print(f"     - {len(chunks)} chunks")
    print(f"     - {page_count} páginas")
    print(f"     - Primero chunk (primeros 200 chars):")
    print(f"       {chunks[0][:200]}...")
except Exception as e:
    print(f"   ❌ Error extrayendo texto: {e}")
    traceback.print_exc()
    exit(1)

# Paso 4: Generar embeddings
print(f"\n4️⃣  Generando embeddings para los {len(chunks)} chunks...")
try:
    embedding_svc = EmbeddingService()
    embeddings = embedding_svc.generar_embeddings_batch(chunks)
    print(f"   ✓ {len(embeddings)} embeddings generados")
    print(f"   Dimensiones: {len(embeddings[0])} números por chunk")
    print(f"   Primeros 5 números del primer embedding:")
    print(f"     {embeddings[0][:5]}")
except Exception as e:
    print(f"   ❌ Error generando embeddings: {e}")
    traceback.print_exc()
    exit(1)

# Paso 5: Mostrar similitud entre chunks
print(f"\n5️⃣  Calculando similitudes entre chunks:")

def cosine_similarity(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x ** 2 for x in a) ** 0.5
    norm_b = sum(x ** 2 for x in b) ** 0.5
    return dot / (norm_a * norm_b) if norm_a * norm_b != 0 else 0

# Comparar primeros 3 chunks
for i in range(min(3, len(chunks) - 1)):
    for j in range(i + 1, min(4, len(chunks))):
        sim = cosine_similarity(embeddings[i], embeddings[j])
        print(f"   Chunk {i} vs Chunk {j}: {sim:.4f}")
        print(f"     - Chunk {i}: {chunks[i][:80]}...")
        print(f"     - Chunk {j}: {chunks[j][:80]}...")

# Paso 6: Lo que sucede en Pinecone
print(f"\n6️⃣  Lo que sucede cuando esto se sube a Pinecone:")
print(f"   Cada chunk + embedding se almacena como:")
print(f"   {{")
print(f"     'id': 'doc-{doc.id}-chunk-0',")
print(f"     'values': {embeddings[0][:3]} + ... (1536 números),")
print(f"     'metadata': {{")
print(f"       'document_id': {doc.id},")
print(f"       'document_name': '{doc.original_filename}',")
print(f"       'chunk_index': 0,")
print(f"       'text': '{chunks[0][:50]}...'")
print(f"     }}")
print(f"   }}")

print(f"\n7️⃣  Cuando el usuario pregunta:")
print(f"   a) La pregunta se convierte a embedding (igual que hicimos aquí)")
print(f"   b) Pinecone busca qué chunks tienen embeddings más similares")
print(f"   c) Devuelve los top 5 chunks relevantes")
print(f"   d) El LLM ve esos 5 chunks + la pregunta")
print(f"   e) El LLM genera la respuesta basado en esos 5 chunks")

print("\n" + "=" * 70)
print("Conceptos entendidos:")
print("  ✓ Embedding = números que representan el significado")
print("  ✓ Similitud coseno = cómo mide Pinecone si dos chunks hablan de lo mismo")
print("  ✓ Metadata = información que acompaña al embedding (cuál documento, qué chunk)")
print("=" * 70)
print("\nSiguiente: 02_pinecone_busqueda.py — buscar en Pinecone y ver qué encuentra")
print("=" * 70)

db.close()
