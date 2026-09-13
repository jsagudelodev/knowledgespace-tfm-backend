"""Almacenamiento de archivos en AWS S3: subida, descarga y URLs firmadas.
Los documentos se guardan aquí; su texto indexado vive en Pinecone y sus
metadatos en PostgreSQL."""
import io

import boto3
from botocore.exceptions import ClientError
from fastapi import UploadFile

from app.core.config import settings


class S3Service:
    """
    Servicio para almacenamiento de archivos en AWS S3.

    Encapsula toda la interacción con boto3 — el resto de la app
    nunca importa boto3 directamente, solo usa esta clase.
    """

    def __init__(self):
        # Cliente S3 autenticado con las credenciales del .env
        self.cliente = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION,
        )
        self.bucket = settings.S3_BUCKET_NAME

    @staticmethod
    def construir_key(company_id: int, nombre_archivo: str) -> str:
        """
        Construye la ruta (key) del objeto dentro del bucket.

        Organizar por empresa garantiza aislamiento multi-tenant:
        cada empresa solo puede ver sus propios archivos.

        Ejemplo: company-5/abc123def456.pdf
        """
        return f"company-{company_id}/{nombre_archivo}"

    def subir_archivo(self, archivo: UploadFile, key: str) -> str:
        """
        Sube un archivo a S3 y retorna su key.

        La key se guarda en la BD como file_path — reemplaza
        la ruta local que se usaba antes (uploads/abc.pdf).
        """
        self.cliente.upload_fileobj(
            archivo.file,
            self.bucket,
            key,
            ExtraArgs={"ContentType": archivo.content_type},
        )
        return key

    def descargar_a_memoria(self, key: str) -> io.BytesIO:
        """
        Descarga un objeto de S3 y lo retorna como buffer en memoria.

        io.BytesIO actúa como un archivo sin escribir nada en disco —
        PyPDF2 puede leerlo igual que si fuera un archivo local.
        """
        try:
            objeto = self.cliente.get_object(Bucket=self.bucket, Key=key)
            return io.BytesIO(objeto["Body"].read())
        except ClientError as e:
            raise Exception(f"Error descargando archivo de S3: {e}")

    def eliminar_archivo(self, key: str) -> None:
        """
        Elimina un objeto del bucket.

        Siempre llamar esto antes de borrar el registro de la BD
        para evitar archivos huérfanos en S3.
        """
        try:
            self.cliente.delete_object(Bucket=self.bucket, Key=key)
        except ClientError as e:
            raise Exception(f"Error eliminando archivo de S3: {e}")

    def generar_url_temporal(self, key: str, segundos: int = 3600) -> str:
        """
        Genera una URL firmada para descargar el archivo de forma segura.

        La URL expira automáticamente después de `segundos` (default 1 hora).
        No expone las credenciales de AWS — solo prueba que la app las tiene.
        """
        try:
            return self.cliente.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": key},
                ExpiresIn=segundos,
            )
        except ClientError as e:
            raise Exception(f"Error generando URL temporal: {e}")
