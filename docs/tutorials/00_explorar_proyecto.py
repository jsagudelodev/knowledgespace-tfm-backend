#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SCRIPT 0: Explora qué datos tienes en el proyecto
Corre esto primero para ver con qué trabajar en los tutoriales
"""
import os
import sys
sys.stdout.reconfigure(encoding='utf-8')
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "api"))
sys.path.insert(0, os.getcwd())

from app.core.database import SessionLocal
from app.db.models.company import Company
from app.db.models.assistant import Assistant
from app.db.models.document import Document
from app.db.models.user import User

db = SessionLocal()

print("=" * 70)
print("INVENTARIO DE DATOS EN TU PROYECTO")
print("=" * 70)

# Empresas
print("\n📊 EMPRESAS:")
companies = db.query(Company).all()
if not companies:
    print("   (Ninguna)")
else:
    for c in companies:
        print(f"   #{c.id}: {c.name}")

# Usuarios
print("\n👥 USUARIOS:")
users = db.query(User).limit(10).all()
if not users:
    print("   (Ninguno)")
else:
    for u in users:
        print(f"   #{u.id}: {u.full_name} ({u.email}) - empresa #{u.company_id}")

# Asistentes
print("\n🤖 ASISTENTES:")
assistants = db.query(Assistant).all()
if not assistants:
    print("   (Ninguno)")
else:
    for a in assistants:
        print(f"   #{a.id}: {a.name} - empresa #{a.company_id} - modelo: {a.model}")

# Documentos
print("\n📄 DOCUMENTOS (primeros 20):")
docs = db.query(Document).limit(20).all()
if not docs:
    print("   (Ninguno)")
else:
    for d in docs:
        status = d.status if hasattr(d, 'status') else '?'
        print(f"   #{d.id}: {d.original_filename} - empresa #{d.company_id} - estado: {status}")

# Resumen
print("\n" + "=" * 70)
print("RECOMENDACIÓN PARA LOS TUTORIALES:")
if companies and assistants and docs:
    c = companies[0]
    a = assistants[0]
    print(f"\nUsa estos valores en los tutoriales:")
    print(f"  COMPANY_ID = {c.id}  (empresa: {c.name})")
    print(f"  ASSISTANT_ID = {a.id}  (asistente: {a.name})")
    print(f"\nTienes {len(docs)} documentos para practicar")
elif companies:
    print(f"\nTienes {len(companies)} empresa(s), pero:")
    if not assistants:
        print("  - Crea un asistente primero en el frontend")
    if not docs:
        print("  - Sube un documento primero en el frontend")
else:
    print("\nCrea datos en el frontend primero:")
    print("  1. Una empresa")
    print("  2. Un asistente")
    print("  3. Sube un documento")

print("=" * 70)

db.close()
