# Implementación de AWS S3 — Almacenamiento de Documentos

> **Propósito:** Reemplazar el almacenamiento local en disco (`uploads/`) por AWS S3,
> que persiste entre reinicios de Docker, escala horizontalmente y tiene respaldo automático.

---

## ¿Por qué necesitamos S3?

| Problema actual (disco local) | Solución con S3 |
|-------------------------------|-----------------|
| Los archivos se pierden al reiniciar Docker | S3 es independiente del servidor |
| No funciona con múltiples instancias del servidor | Todas las instancias leen del mismo bucket |
| Sin respaldo automático | S3 ofrece versionado y replicación |
| Almacenamiento limitado al disco del servidor | Almacenamiento ilimitado, pago por uso |

---

## Conceptos Clave (leer antes de implementar)

### ¿Qué es S3?
S3 (Simple Storage Service) es el servicio de almacenamiento de archivos de AWS.
Los archivos se llaman **objetos** y viven dentro de un **bucket** (como una carpeta raíz).
Cada objeto tiene una **key** que funciona como su ruta dentro del bucket.

```
Bucket: knowledgespace-documentos
  └── empresa-5/
        └── documentos/
              └── abc123.pdf   ← esto es la key del objeto
```

### ¿Qué es IAM?
IAM (Identity and Access Management) es el sistema de permisos de AWS.
En lugar de darle las credenciales de tu cuenta principal a la aplicación,
se crea un **usuario IAM** con permisos mínimos (**principio de mínimo privilegio**):
solo puede acceder a S3 y nada más. Si esas credenciales se filtran, el daño es limitado.

### ¿Qué es una Presigned URL?
Es una URL temporal firmada criptográficamente que permite descargar un archivo
privado de S3 sin exponer las credenciales. Caduca después de N segundos (ej: 1 hora).

```
https://bucket.s3.amazonaws.com/empresa-5/abc123.pdf?X-Amz-Firma=...&X-Amz-Expira=3600
```

---

## Paso 1 — Configurar AWS (Consola Web)

### 1.1 Crear el Bucket S3

1. Entrar a [console.aws.amazon.com](https://console.aws.amazon.com)
2. En el buscador de arriba escribir **S3** → entrar al servicio
3. Hacer clic en **"Create bucket"**
4. Configurar los campos:

| Campo | Valor |
|-------|-------|
| Nombre del bucket | `knowledgespace-documentos` (debe ser único globalmente en AWS) |
| Región de AWS | La más cercana a tus usuarios (ej: `us-east-1` para EE.UU. Este) |
| Bloquear todo acceso público | ✅ Activado — los archivos NO serán públicos |
| Versionado | Desactivado por ahora |

5. Hacer clic en **"Create bucket"**

> **¿Por qué bloquear el acceso público?**
> Los PDFs de las empresas son confidenciales. La aplicación los entregará
> con URLs temporales (presigned URLs), no con URLs públicas permanentes.

---

### 1.2 Crear el Usuario IAM

1. En el buscador de AWS escribir **IAM** → entrar al servicio
2. En el menú izquierdo: **Usuarios → Crear usuario**
3. Configurar:

| Campo | Valor |
|-------|-------|
| Nombre de usuario | `knowledgespace-s3-usuario` |
| Permisos | Adjuntar políticas directamente → seleccionar `AmazonS3FullAccess` |

4. Hacer clic en **"Crear usuario"**

> **Nota para aprender:** `AmazonS3FullAccess` es suficiente para desarrollo.
> En producción se crearía una política personalizada que restringe el acceso
> únicamente al bucket `knowledgespace-documentos`, no a todos los buckets.

---

### 1.3 Generar las Credenciales de Acceso

1. Entrar al usuario recién creado → pestaña **"Credenciales de seguridad"**
2. Bajar hasta **"Claves de acceso"** → **"Crear clave de acceso"**
3. Caso de uso: **"Aplicación que se ejecuta fuera de AWS"**
4. Copiar y guardar los dos valores:

```
AWS_ACCESS_KEY_ID=AKIA...............
AWS_SECRET_ACCESS_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

> **Importante:** La clave de acceso secreta solo se muestra una vez.
> Guardarla inmediatamente. Si se pierde, hay que crear una nueva.

---

## Paso 2 — Instalar boto3

`boto3` es el SDK oficial de AWS para Python. Permite interactuar con S3 (y todos
los servicios de AWS) desde código Python.

**Agregar a** `api/requirements.txt`:

```
boto3==1.34.0
```

**Instalar en el entorno virtual:**

```bash
pip install boto3==1.34.0
```

---

## Paso 3 — Variables de Entorno

### ¿Por qué variables de entorno?
Las credenciales de AWS nunca deben estar escritas directamente en el código.
Si alguien accede al repositorio, no debe poder ver las claves.
Las variables de entorno se cargan desde un archivo `.env` que **no se commitea a Git**.

**Agregar a** `api/.env`:

```bash
AWS_ACCESS_KEY_ID=AKIA...............
AWS_SECRET_ACCESS_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
AWS_REGION=us-east-1
AWS_S3_BUCKET=knowledgespace-documentos
```

**Agregar a** `api/app/core/config.py` dentro de la clase `Settings`:

```python
# Configuración AWS S3
AWS_ACCESS_KEY_ID: str
AWS_SECRET_ACCESS_KEY: str
AWS_REGION: str = "us-east-1"
AWS_S3_BUCKET: str
```

---

## Paso 4 — Crear el S3Service

**Archivo nuevo:** `api/app/services/s3_service.py`

Este servicio encapsula toda la interacción con S3. El resto de la aplicación
nunca llama a `boto3` directamente — siempre usa `S3Service`.
Esto se llama **encapsulamiento** y facilita cambiar de proveedor en el futuro.

### Métodos del servicio

| Método | Qué hace |
|--------|----------|
| `construir_key(empresa_id, nombre_archivo)` | Construye la ruta del objeto: `empresa-5/abc123.pdf` |
| `subir_archivo(archivo, key)` | Sube el archivo al bucket, retorna la key |
| `eliminar_archivo(key)` | Elimina un objeto del bucket |
| `generar_url_temporal(key, segundos)` | Genera URL firmada de descarga (presigned URL) |

### Código completo

```python
# api/app/services/s3_service.py
import boto3
from botocore.exceptions import ClientError
from fastapi import UploadFile

from app.core.config import settings


class S3Service:
    """
    Servicio para almacenamiento de archivos en AWS S3.
    Encapsula toda la interacción con boto3.
    """

    def __init__(self):
        # Crear cliente de S3 con las credenciales de config.py
        self.cliente = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION,
        )
        self.bucket = settings.AWS_S3_BUCKET

    @staticmethod
    def construir_key(empresa_id: int, nombre_archivo: str) -> str:
        """
        Construye la key (ruta) del objeto dentro del bucket.
        Ejemplo: empresa-5/abc123def.pdf
        Organizar por empresa garantiza el aislamiento multi-tenant.
        """
        return f"empresa-{empresa_id}/{nombre_archivo}"

    def subir_archivo(self, archivo: UploadFile, key: str) -> str:
        """
        Sube un archivo a S3.
        - archivo: el archivo recibido en el endpoint FastAPI
        - key: la ruta dentro del bucket (resultado de construir_key)
        Retorna la key del objeto subido (se guarda en la BD como file_path).
        """
        self.cliente.upload_fileobj(
            archivo.file,            # stream del archivo
            self.bucket,             # nombre del bucket
            key,                     # ruta dentro del bucket
            ExtraArgs={"ContentType": archivo.content_type},  # tipo MIME
        )
        return key

    def eliminar_archivo(self, key: str) -> None:
        """Elimina un objeto del bucket dado su key."""
        try:
            self.cliente.delete_object(Bucket=self.bucket, Key=key)
        except ClientError as e:
            raise Exception(f"Error eliminando archivo de S3: {e}")

    def generar_url_temporal(self, key: str, segundos: int = 3600) -> str:
        """
        Genera una URL temporal firmada para descargar el archivo.
        - key: ruta del objeto en S3
        - segundos: tiempo de vida de la URL (por defecto 1 hora)
        La URL expira automáticamente — no hay acceso permanente.
        """
        try:
            url = self.cliente.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": key},
                ExpiresIn=segundos,
            )
            return url
        except ClientError as e:
            raise Exception(f"Error generando URL temporal: {e}")
```

---

## Paso 5 — Integrar S3 en el Router de Documentos

**Archivo:** `api/app/routers/v1/documents.py`

Reemplazar el bloque que guarda en disco local por una llamada a `S3Service`.

**Código anterior (filesystem):**
```python
upload_dir = "uploads"
os.makedirs(upload_dir, exist_ok=True)
file_path = os.path.join(upload_dir, safe_filename)
with open(file_path, "wb") as buffer:
    shutil.copyfileobj(file.file, buffer)
```

**Código nuevo (S3):**
```python
s3 = S3Service()
key = S3Service.construir_key(current_user.company_id, safe_filename)
file_path = s3.subir_archivo(file, key)   # file_path ahora es la key de S3
```

> **Qué cambia en la BD:** El campo `file_path` pasa de guardar una ruta local
> (`uploads/abc123.pdf`) a guardar la key de S3 (`empresa-5/abc123.pdf`).
> La estructura de la BD no cambia, solo el contenido del campo.

También eliminar los imports que ya no se necesitan:
```python
# Eliminar estas líneas del import:
import os
import shutil
```

---

## Paso 6 — Actualizar PDFService para leer desde S3

**Archivo:** `api/app/services/pdf_service.py`

El servicio actual lee el PDF desde disco con `open(file_path, 'rb')`.
Con S3, primero se descarga el contenido a memoria y se procesa desde ahí.

**Código anterior:**
```python
with open(file_path, 'rb') as archivo:
    lector = PyPDF2.PdfReader(archivo)
```

**Código nuevo:**
```python
import io
import boto3

# Descargar el objeto desde S3 a memoria (sin escribir en disco)
cliente_s3 = boto3.client("s3", ...)
objeto_s3 = cliente_s3.get_object(Bucket=bucket, Key=key)
bytes_archivo = io.BytesIO(objeto_s3["Body"].read())
lector = PyPDF2.PdfReader(bytes_archivo)
```

> **Concepto clave:** `io.BytesIO` es un "archivo en memoria" (buffer de bytes).
> PyPDF2 no distingue si está leyendo desde disco o desde memoria
> — solo necesita un objeto que se comporte como un archivo.

---

## Paso 7 — Eliminar de S3 al borrar un Documento

**Archivo:** `api/app/routers/v1/documents.py` — endpoint DELETE

Cuando se elimina un documento de la BD, también hay que eliminarlo de S3.
Si solo se borra de la BD, el archivo queda huérfano en S3 (ocupa espacio y genera costos).

**Código actualizado:**
```python
@router.delete("/{documento_id}", status_code=204)
async def eliminar_documento(documento_id: int, ...):
    db_documento = repo.get(documento_id)
    if not db_documento or db_documento.company_id != usuario_actual.company_id:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    # Paso 1: Eliminar de S3 primero (si falla S3, no borramos de la BD)
    s3 = S3Service()
    s3.eliminar_archivo(db_documento.file_path)   # file_path contiene la key de S3

    # Paso 2: Eliminar de la BD
    repo.delete(db_documento)
    return None
```

> **¿Por qué eliminar S3 primero?**
> Si primero borramos de la BD y luego falla S3, el archivo queda huérfano para siempre.
> Si primero borramos de S3 y luego falla la BD, el registro sigue en la BD y el
> usuario puede intentar de nuevo. El orden importa para mantener consistencia.

---

## Resumen de Archivos Modificados

| Archivo | Tipo de cambio |
|---------|----------------|
| `api/requirements.txt` | Agregar `boto3==1.34.0` |
| `api/.env` | Agregar 4 variables AWS (no commitear) |
| `api/app/core/config.py` | Declarar las 4 variables en la clase `Settings` |
| `api/app/services/s3_service.py` | **Archivo nuevo** — S3Service completo |
| `api/app/routers/v1/documents.py` | Upload usa S3; Delete también borra de S3 |
| `api/app/services/pdf_service.py` | Leer PDF desde S3 en vez de disco local |

---

## Lista de Verificación Final

Una vez implementado, verificar que todo funcione:

- [ ] Subir un PDF → aparece en el bucket S3 en la consola de AWS
- [ ] El campo `file_path` en la BD contiene `empresa-{id}/uuid.pdf` (no una ruta local)
- [ ] Eliminar un documento desde la app → el objeto desaparece del bucket S3
- [ ] Reiniciar el servidor → los archivos siguen disponibles (no se pierden)
- [ ] El `.env` no está commitado en Git (verificar `.gitignore`)
