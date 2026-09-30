import os
import sys




sys.stdout.reconfigure(encoding='utf-8')
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "api"))
sys.path.insert(0, os.getcwd())


from app.core.database import SessionLocal
from app.db.models.company import Company
from app.db.models.user import User
from app.db.models.assistant import Assistant
db=SessionLocal()

print("=" * 70)
print("INVENTARIO DE DATOS EN TU PROYECTO")
print("=" * 70)


print("\n📊 EMPRESAS:")

empresas=db.query(Company).all()
if not empresas:
    print("   (Ninguna)")
else:
    for c in empresas:
        print(f" #{c.id}: {c.name}")




print ("=" * 70)
print("\n Usuarios")

usuarios=db.query(User).all()
if not usuarios:
    print("   (Ninguno)")
else:
    for u in usuarios:
        print(f" #{u.id}: {u.email} - {u.full_name}")



print ("=" * 70)
print("\n Asistentes")



asistentes=db.query(Assistant).all()
if not asistentes:
    print("   (Ninguno)")
else:
    for a in asistentes:
        print(f" #{a.id}: {a.name} - {a.description} - {a.company_id}")  



















