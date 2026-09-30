#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TUTORIAL 3 (REAL): El flujo RAG completo en acción

Este es el mayor — demuestra end-to-end:
1. Pregunta del usuario
2. Buscar en Pinecone
3. Construir el prompt para el LLM
4. Ver la respuesta del LLM
5. Ver cómo evitamos alucinaciones

IMPORTANTE: Esto llama a OpenAI. Tiene costo (minimal pero real).

Edita QUERY y ASSISTANT_ID abajo.

Ejecutar:
  python docs/tutorials/03_rag_completo.py
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
from app.services.rag_service import RAGService
import traceback

# ─── EDITA ESTO ───────────────────────────────────────────────────────
QUERY = "¿Qué es NLP?"  # Tu pregunta
ASSISTANT_ID = 2  # VCD (asistente con documentos)
COMPANY_ID = 8  # KnowledgeSpace Demo
# ───────────────────────────────────────────────────────────────────────

db = SessionLocal()

print("=" * 80)
print("TUTORIAL 3: FLUJO RAG COMPLETO — Cómo el LLM responde")
print("=" * 80)

# Paso 0: Verificar asistente
print(f"\n0️⃣  Verificando datos...")
assistant = db.query(Assistant).filter(Assistant.id == ASSISTANT_ID).first()
if not assistant:
    print(f"   ❌ Asistente #{ASSISTANT_ID} no encontrado")
    exit(1)
print(f"   ✓ Asistente: {assistant.name}")
print(f"   ✓ Modelo LLM: {assistant.model}")
print(f"   ✓ Prompt del asistente: {assistant.system_prompt[:100] if assistant.system_prompt else '(vacío, usa default)'}...")

# Paso 1: Simular RAGService completo
print(f"\n1️⃣  Ejecutando RAGService.generate_response()...")
print(f"   (Esto hace TODOS los pasos: embedding → Pinecone → LLM)")
try:
    rag_service = RAGService()
    response = rag_service.generate_response(
        query=QUERY,
        company_id=COMPANY_ID,
        assistant_id=ASSISTANT_ID,
        system_prompt_override=assistant.system_prompt,
    )

    print(f"   ✓ Respuesta generada")

    # Desglosar la respuesta
    content = response.get("content", "")
    sources = response.get("sources", [])
    input_tokens = response.get("input_tokens", 0)
    output_tokens = response.get("output_tokens", 0)
    model = response.get("model", "?")

    print(f"\n2️⃣  Desglose de la respuesta:")
    print(f"   Modelo usado: {model}")
    print(f"   Tokens entrada: {input_tokens}")
    print(f"   Tokens salida: {output_tokens}")
    print(f"   Total costo (aprox): ${0.00015 * input_tokens / 1000 + 0.0006 * output_tokens / 1000:.6f}")

except Exception as e:
    print(f"   ❌ Error: {e}")
    traceback.print_exc()
    exit(1)

# Paso 2: Mostrar la respuesta
print(f"\n3️⃣  LA RESPUESTA DEL LLM:")
print(f"   {content}")

# Paso 3: Mostrar las fuentes
print(f"\n4️⃣  FUENTES CITADAS:")
if not sources:
    print(f"   (Ninguna — el LLM respondió basado en su conocimiento interno)")
    print(f"   ⚠️  Esto es donde ocurren las ALUCINACIONES si no hay controles")
else:
    for i, source in enumerate(sources, 1):
        doc_name = source.get("document_name", "?")
        score = source.get("score", 0)
        text = source.get("text", "?")
        print(f"\n   [{i}] {doc_name} (score: {score:.3f})")
        print(f"       {text[:120]}...")

# Paso 4: Explicar cómo evitamos alucinaciones
print(f"\n5️⃣  ¿CÓMO EVITAMOS ALUCINACIONES?")
print(f"\n   Control 1: RELEVANCE_THRESHOLD = 0.30")
print(f"   - Chunks con score < 0.30 NO se envían al LLM")
print(f"   - Evita que evidencia débil parezca fuerte")

print(f"\n   Control 2: PROMPT RESTRICTIVO")
print(f"   - El system_prompt ordena al LLM:")
print(f"     'USA SOLO la información del contexto'")
print(f"     'NUNCA uses conocimiento externo'")
print(f"     'Si no hay contexto, di: No encontré información...'")

print(f"\n   Control 3: AISLAMIENTO POR ESPACIO")
print(f"   - Si buscas en namespace del asistente A")
print(f"   - No ves documentos del asistente B")
print(f"   - Evita 'confundir' espacios")

print(f"\n   Control 4: VERIFICACIÓN POST-RESOLUCIÓN")
print(f"   - Si algo no se encuentra, se registra como 'pregunta sin respuesta'")
print(f"   - Admins pueden llenar el hueco")
print(f"   - Sistema detecta si el hueco se resolvió de verdad")

# Paso 5: Lo que vería un usuario en el chat
print(f"\n6️⃣  EN LA INTERFAZ DEL CHAT, EL USUARIO VE:")
print(f"   Pregunta: {QUERY}")
print(f"   Respuesta: {content}")
print(f"   Costo: ${0.00015 * input_tokens / 1000 + 0.0006 * output_tokens / 1000:.6f}")
print(f"   Fuentes: {len(sources)} documento(s) citado(s)")

# Paso 6: Flujo visual
print(f"\n7️⃣  FLUJO VISUAL COMPLETO:")
print(f"""
   Usuario: "{QUERY}"
        ↓
   Embedding: Convertir a números
        ↓
   Pinecone: Buscar chunks similares
        ↓
   Filtro: Score >= 0.30?
        ├─ SÍ → Construir contexto
        │       ↓
        │   LLM: Lee contexto + pregunta
        │       ↓
        │   Respuesta: "{content[:50]}..."
        │       ↓
        │   Usuario ve: respuesta + fuentes + $costo
        │
        └─ NO → LLM ve contexto vacío
                ↓
            Respuesta: "No encontré información..."
                ↓
            Registrar como: knowledge_gap
                ↓
                (Admins pueden resolverlo manualmente)
""")

print("\n" + "=" * 80)
print("Conceptos entendidos:")
print("  ✓ Embedding: convertir texto a números")
print("  ✓ Búsqueda: encontrar chunks similares en Pinecone")
print("  ✓ Prompt restrictivo: ordena al LLM no alucinar")
print("  ✓ Aislamiento: cada espacio vive en su namespace")
print("  ✓ Verificación: preguntas sin respuesta se registran")
print("  ✓ RAG: Retrieval (Pinecone) + Augmentation (contexto) + Generation (LLM)")
print("=" * 80)

print("\n✅ PRÓXIMO PASO:")
print("   Prueba editando QUERY en este mismo script para ver cómo responde")
print("   a preguntas diferentes. Observa:")
print("   - Cómo cambian los chunks recuperados")
print("   - Si tiene fuentes o no")
print("   - El costo de cada pregunta")

db.close()
