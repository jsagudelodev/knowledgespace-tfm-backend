import os
import sys
sys.stdout.reconfigure(encoding='utf-8')
os.chdir(r"D:\Proyectos\GitHub\Sass\KnowledgeSpace\api")
sys.path.insert(0, os.getcwd())
from app.db.models.document import Document
from  app.services.s3_service import S3Service
from app.services.pdf_service import PDFService






from app.core.database import SessionLocal

db=SessionLocal()



print("=" * 70)
print("DOCUMENTOS")

doc=db.query(Document).filter(Document.id == 42).first()

if not doc:
    print(f"   ❌ Documento #1 no encontrado")
    print(f"   Corre primero: 00_explorar_proyecto.py")
else:
    print(f"   ✓ Encontrado: {doc.original_filename}")
    print(f"   Tamaño: {doc.file_size} bytes")
    print(f"   Nombre: {doc.filename} ")


# Paso 2: Descargar el archivo desde S3

try:
    s3 = S3Service()
    buffer = s3.descargar_a_memoria(doc.file_path)
    print(f"   ✓ Descargado ({len(buffer.getvalue())} bytes en memoria)")

except Exception as ex:
    print(f"Error{ex}")
finally:
    print("")



# Paso 3: Extraer texto según tipo de archivo
print(f"\n3️⃣  Extrayendo texto del archivo ({doc.mime_type})...")
file_type = doc.filename.split(".")[-1].lower()
chunks, page_count = PDFService.procesar(doc.file_path, file_type=file_type)
print(file_type)





    

