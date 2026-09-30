#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TUTORIAL 2 (REAL): Búsqueda en Pinecone con tus datos

Este script:
1. Toma una pregunta que ESCRIBES
2. La convierte a embedding
3. Busca en Pinecone qué documentos del proyecto responden eso
4. Te muestra exactamente qué chunks encontró y con qué "score" de similitud

Edita QUERY y ASSISTANT_ID abajo.

Ejecutar:
  python docs/tutorials/02_pinecone_busqueda.py
"""
import os
import sys
sys.stdout.reconfigure(encoding='utf-8')
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "api"))
sys.path.insert(0, os.getcwd())

from app.core.database import SessionLocal
from app.db.models.assistant import Assistant
from app.services.embedding_service import EmbeddingService
from app.services.pinecone_service import PineconeService
import traceback

# ─── EDITA ESTO ───────────────────────────────────────────────────────
QUERY = "¿Qué es NLP y embeddings?"  # Tu pregunta
ASSISTANT_ID = 2  # VCD (asistente que tiene documentos)
COMPANY_ID = 8  # KnowledgeSpace Demo
# ───────────────────────────────────────────────────────────────────────

db = SessionLocal()

print("=" * 70)
print("TUTORIAL 2: BÚSQUEDA EN PINECONE")
print("=" * 70)

# Paso 1: Verificar asistente
print(f"\n1️⃣  Verificando asistente...")
assistant = db.query(Assistant).filter(Assistant.id == ASSISTANT_ID).first()
if not assistant:
    print(f"   ❌ Asistente #{ASSISTANT_ID} no encontrado")
    print(f"   Corre: 00_explorar_proyecto.py")
    exit(1)
print(f"   ✓ Asistente: {assistant.name}")

# Paso 2: Convertir pregunta a embedding
print(f"\n2️⃣  Convirtiendo tu pregunta a embedding...")
print(f"   Pregunta: '{QUERY}'")
try:
    embedding_svc = EmbeddingService()
    query_embedding = embedding_svc.generar_embeddings_batch([QUERY])[0]
    print(f"   ✓ Embedding generado ({len(query_embedding)} dimensiones)")
    print(f"   Primeros 5 números: {query_embedding[:5]}")
except Exception as e:
    print(f"   ❌ Error: {e}")
    traceback.print_exc()
    exit(1)

# Paso 3: Buscar en Pinecone
print(f"\n3️⃣  Buscando en Pinecone...")

namespace = PineconeService.construir_namespace(COMPANY_ID, ASSISTANT_ID)
print(f"   Namespace: {namespace}")
print(f"   (namespace = nombre del compartimento en Pinecone para este asistente)")

try:
    pinecone_svc = PineconeService()
    results = pinecone_svc.buscar_vectores(
        vector_consulta=query_embedding,
        top_k=5,  # Devuelve los 5 más relevantes
        namespace=namespace
    )

    if not results:
        print(f"   ⚠️  No se encontraron resultados")
        print(f"   (¿Hay documentos subidos para este asistente?)")
    else:
        print(f"   ✓ Encontrados {len(results)} resultados:")

        for rank, result in enumerate(results, 1):
            score = result.get("score", 0)
            metadata = result.get("metadata", {})

            # Interpretar el score
            if score >= 0.7:
                relevance = "🟢 MUY RELEVANTE"
            elif score >= 0.5:
                relevance = "🟡 MODERADO"
            else:
                relevance = "🔴 POCO RELEVANTE"

            print(f"\n      {rank}. [{relevance}] (score: {score:.4f})")
            print(f"         Documento: {metadata.get('document_name', '?')}")
            print(f"         Chunk: #{metadata.get('chunk_index', '?')}")
            print(f"         Texto: {metadata.get('text', '?')[:120]}...")

except Exception as e:
    print(f"   ❌ Error buscando en Pinecone: {e}")
    print(f"   ¿Credenciales de Pinecone en .env?")
    traceback.print_exc()
    exit(1)

# Paso 4: Explicar el score
print(f"\n4️⃣  ¿Qué significa el 'score'?")
print(f"   Score = similitud coseno entre embeddings")
print(f"   0.0 = completamente diferentes (nada que ver)")
print(f"   1.0 = idénticos")
print(f"   El sistema usa score >= 0.30 para 'pasar' a la siguiente etapa (RAG)")

# Paso 5: Mostrar el flujo
print(f"\n5️⃣  El flujo completo es:")
print(f"   a) Usuario pregunta: '{QUERY}'")
print(f"   b) Pregunta → embedding")
print(f"   c) Buscar en Pinecone (namespace del asistente)")
print(f"   d) Filtrar por score >= 0.30 (RELEVANCE_THRESHOLD)")
print(f"   e) Si hay chunks relevantes → construir contexto")
print(f"   f) Enviar contexto + pregunta al LLM (siguiente tutorial)")

print("\n" + "=" * 70)
print("Conceptos entendidos:")
print("  ✓ La pregunta se convierte a embedding")
print("  ✓ Pinecone busca chunks con embeddings similares")
print("  ✓ Score alto = más confianza en el resultado")
print("  ✓ Threshold = corte: debajo no pasamos al LLM")
print("=" * 70)
print("\nSiguiente: 03_rag_completo.py — ver cómo el LLM usa esos chunks")
print("=" * 70)

db.close()
