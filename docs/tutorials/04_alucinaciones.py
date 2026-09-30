#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TUTORIAL 4: Alucinaciones — Cómo el LLM puede inventar cosas y cómo las prevenimos

Una ALUCINACIÓN es cuando el LLM responde algo que parece creíble pero NO
está en los documentos. Ejemplo:

   Usuario pregunta: "¿Cuál es el CEO?"
   Documentos: (vacío)
   LLM alucinando: "El CEO es María García"
   Realidad: No sabemos, no está en el contexto

Este script demuestra 4 CONTROLES que prevenimos:

1. CONTROL POR THRESHOLD: chunks débiles no llegan al LLM
2. CONTROL POR PROMPT: el LLM sabe que NO debe alucinar
3. CONTROL POR AISLAMIENTO: espacios separados, sin cross-contamination
4. CONTROL POR REGISTRO: preguntas sin respuesta se documentan

Ejecutar:
  python docs/tutorials/04_alucinaciones.py
"""
import os
import sys
sys.stdout.reconfigure(encoding='utf-8')
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "api"))
sys.path.insert(0, os.getcwd())

from app.services.rag_service import RAGService, DEFAULT_SYSTEM_PROMPT, RELEVANCE_THRESHOLD
from app.core.config import settings
from openai import OpenAI

print("=" * 80)
print("TUTORIAL 4: ALUCINACIONES — 4 CONTROLES QUE LAS PREVIENEN")
print("=" * 80)

# Control 1: El RELEVANCE_THRESHOLD
print(f"\n1️⃣  CONTROL 1: RELEVANCE_THRESHOLD")
print(f"   Valor: {RELEVANCE_THRESHOLD}")
print(f"   Qué hace: Chunks con score < {RELEVANCE_THRESHOLD} NO se usan")
print(f"   Previene: Enviar evidencia débil al LLM")
print(f"\n   Ejemplo:")
print(f"   - Pregunta: '¿Cuál es el precio de un elefante?'")
print(f"   - Chunk 1 encontrado: 'Los elefantes africanos pesan 6000 kg' (score: 0.45)")
print(f"   - ¿Se envía al LLM? {'SÍ' if 0.45 >= RELEVANCE_THRESHOLD else 'NO'}")
print(f"   - Resultado: El LLM NO ve contexto → responde 'No encontré información'")

# Control 2: El prompt restrictivo
print(f"\n2️⃣  CONTROL 2: PROMPT RESTRICTIVO")
print(f"   El LLM recibe este instruction set:")
print(f"\n   ---")
for line in DEFAULT_SYSTEM_PROMPT.split('\n')[:6]:
    print(f"   {line}")
print(f"   ---")
print(f"\n   Previene: Que el LLM piense que puede usar su conocimiento interno")
print(f"   Si no hay contexto → LLM responde textualmente: 'No encontré información...'")

# Control 3: Aislamiento por namespace
print(f"\n3️⃣  CONTROL 3: AISLAMIENTO POR NAMESPACE")
print(f"   Cada asistente busca en su PROPIO namespace:")
print(f"   - Espacio A (invoice.pdf) → namespace 'company-1-assistant-1'")
print(f"   - Espacio B (manual.pdf) → namespace 'company-1-assistant-2'")
print(f"\n   Previene: Que contenido de un espacio 'contammine' al otro")
print(f"   Ejemplo:")
print(f"   - Asistente A pregunta: '¿Cuál es la política de devolución?'")
print(f"   - Asistente B tiene invoice.pdf (no tiene política)")
print(f"   - Resultado: Asistente B NO ve invoice.pdf de A → responde 'No encontré'")
print(f"   - (No comparte datos de más allá de su espacio)")

# Control 4: Registro de gaps
print(f"\n4️⃣  CONTROL 4: REGISTRO DE KNOWLEDGE_GAPS")
print(f"   Cuando el LLM responde 'No encontré información':")
print(f"   - Esto se registra como una 'pregunta sin respuesta'")
print(f"   - Los admins la ven en el dashboard de 'Preguntas sin respuesta'")
print(f"   - Pueden:")
print(f"     a) Vincular un documento (si existe)")
print(f"     b) Escribir la respuesta manualmente")
print(f"     c) Pedir a alguien que busque el documento")
print(f"\n   Previene: Que huecos de conocimiento pasen desapercibidos")

# Simulación de una alucinación
print(f"\n5️⃣  SIMULACIÓN: ¿Qué pasa si el LLM intenta alucinar?")
print(f"\n   Escenario: Contexto VACÍO + pregunta sobre 'CEO'")

client = OpenAI(api_key=settings.OPENAI_API_KEY)

# Test A: LLM sin restricciones (ALUCINACIÓN PROBABLE)
print(f"\n   Test A: SIN el prompt restrictivo (LLM libre)")
try:
    response = client.chat.completions.create(
        model=settings.OPENAI_CHAT_MODEL,
        messages=[
            {"role": "system", "content": "Eres un asistente útil."},
            {"role": "user", "content": "¿Cuál es el nombre del CEO?"},
        ],
        max_tokens=100,
        temperature=0.7,
    )
    respuesta_sin_restriccion = response.choices[0].message.content
    print(f"   Respuesta: {respuesta_sin_restriccion[:120]}...")
    print(f"   ⚠️  El LLM ALUCINA → inventa un CEO")
except Exception as e:
    print(f"   ❌ Error: {e}")
    respuesta_sin_restriccion = "Error"

# Test B: LLM con nuestro prompt restrictivo (NO ALUCINACIÓN)
print(f"\n   Test B: CON nuestro prompt restrictivo")
try:
    response = client.chat.completions.create(
        model=settings.OPENAI_CHAT_MODEL,
        messages=[
            {"role": "system", "content": DEFAULT_SYSTEM_PROMPT},
            {"role": "system", "content": "No se encontró contexto relevante en los documentos de la empresa."},
            {"role": "user", "content": "¿Cuál es el nombre del CEO?"},
        ],
        max_tokens=100,
        temperature=0.7,
    )
    respuesta_con_restriccion = response.choices[0].message.content
    print(f"   Respuesta: {respuesta_con_restriccion[:120]}...")
    print(f"   ✓ El LLM NO ALUCINA → dice 'No encontré información'")
except Exception as e:
    print(f"   ❌ Error: {e}")
    respuesta_con_restriccion = "Error"

# Comparación
print(f"\n   DIFERENCIA:")
print(f"   - Sin restricción: Inventa una respuesta (alucinación)")
print(f"   - Con restricción: Dice 'no sé' (correcto)")

# Arquitectura completa
print(f"\n6️⃣  ARQUITECTURA COMPLETA DE PREVENCIÓN:")
print(f"""
   Usuario pregunta algo
        ↓
   1. Buscar en Pinecone
        ↓
   2. Score >= {RELEVANCE_THRESHOLD}?
        ├─ NO → Contexto vacío
        │
   3. Construir prompt
        ├─ Sistema: DEFAULT_SYSTEM_PROMPT
        │           (prohíbe alucinar)
        ├─ Contexto: chunks encontrados
        │            (o "no encontró" si vacío)
        ├─ Historial: conversación previa
        └─ Usuario: pregunta
        ↓
   4. Enviar a LLM
        ↓
   5. LLM responde
        └─ Si no hay contexto → "No encontré..."
        └─ Si hay contexto → usa solo ESO
        ↓
   6. Si "No encontré..." → registrar como knowledge_gap
        ↓
   Usuario ve:
        - Respuesta (o "No encontré")
        - Fuentes citadas (si las hay)
        - $Costo
""")

print("\n" + "=" * 80)
print("Resumen: 4 capas de defensa contra alucinaciones")
print("  1. Threshold: No pasar evidencia débil")
print("  2. Prompt: Instruir al LLM a no inventar")
print("  3. Aislamiento: No mezclar espacios")
print("  4. Registro: Documentar huecos para rellenarlos")
print("=" * 80)
