"""Etapa de ingesta del pipeline RAG: extracción de texto (PDF/DOCX/TXT) y
división en chunks. Los PDFs pasan por tres parsers en cascada porque ninguno
solo cubre todos los casos — ver `_extraer_pdf` y `docs/RAG_PIPELINE.md` §3."""
import io
from typing import List, Tuple

from app.services.s3_service import S3Service


class PDFService:
    """
    Extracción de texto para documentos almacenados en S3.

    Estrategia por tipo:
    - PDF:  pymupdf como parser principal (mejor para PDFs complejos y escaneados);
            pdfplumber como fallback (mejor para tablas y layouts en columnas);
            PyPDF2 como último recurso.
    - DOCX: python-docx (párrafos + tablas).
    - TXT:  lectura directa UTF-8.

    Nunca escribe en disco — todo en memoria (io.BytesIO).
    """

    # ── Descarga desde S3 ────────────────────────────────────────────────────

    @staticmethod
    def _obtener_buffer(s3_key: str) -> io.BytesIO:
        return S3Service().descargar_a_memoria(s3_key)

    # ── PDF ──────────────────────────────────────────────────────────────────

    @staticmethod
    def _extraer_texto_pymupdf(buffer: io.BytesIO) -> Tuple[str, int]:
        """Parser principal — pymupdf (fitz). Maneja PDFs complejos y escaneados."""
        import fitz  # PyMuPDF
        buffer.seek(0)
        doc = fitz.open(stream=buffer.read(), filetype="pdf")
        texto = "\n".join(page.get_text() for page in doc)
        paginas = len(doc)
        doc.close()
        return texto, paginas

    @staticmethod
    def _extraer_texto_pdfplumber(buffer: io.BytesIO) -> Tuple[str, int]:
        """Fallback — pdfplumber. Mejor para tablas y layouts en columnas."""
        import pdfplumber
        buffer.seek(0)
        with pdfplumber.open(buffer) as pdf:
            texto = "\n".join(
                page.extract_text() or ""
                for page in pdf.pages
            )
            paginas = len(pdf.pages)
        return texto, paginas

    @staticmethod
    def _extraer_texto_pypdf2(buffer: io.BytesIO) -> Tuple[str, int]:
        """Último recurso — PyPDF2."""
        import PyPDF2
        buffer.seek(0)
        lector = PyPDF2.PdfReader(buffer)
        texto = "\n".join(
            pagina.extract_text() or ""
            for pagina in lector.pages
        )
        return texto, len(lector.pages)

    @staticmethod
    def _extraer_pdf(buffer: io.BytesIO) -> Tuple[str, int]:
        """
        Intenta parsear el PDF con tres parsers en cascada.
        Si el texto extraído es demasiado corto, pasa al siguiente.
        """
        for parser in (
            PDFService._extraer_texto_pymupdf,
            PDFService._extraer_texto_pdfplumber,
            PDFService._extraer_texto_pypdf2,
        ):
            try:
                texto, paginas = parser(buffer)
                if len(texto.strip()) > 50:
                    return texto, paginas
            except Exception:
                continue
        raise Exception("No se pudo extraer texto del PDF con ningún parser disponible")

    # ── DOCX ─────────────────────────────────────────────────────────────────

    @staticmethod
    def _extraer_docx(buffer: io.BytesIO) -> Tuple[str, int]:
        """Extrae párrafos y celdas de tabla de un DOCX."""
        from docx import Document as DocxDocument
        buffer.seek(0)
        doc = DocxDocument(buffer)

        partes = [p.text for p in doc.paragraphs if p.text.strip()]

        for tabla in doc.tables:
            for fila in tabla.rows:
                fila_texto = " | ".join(c.text.strip() for c in fila.cells if c.text.strip())
                if fila_texto:
                    partes.append(fila_texto)

        texto = "\n".join(partes)
        paginas = max(1, len(doc.paragraphs) // 20)
        return texto, paginas

    # ── TXT ──────────────────────────────────────────────────────────────────

    @staticmethod
    def _extraer_txt(buffer: io.BytesIO) -> Tuple[str, int]:
        buffer.seek(0)
        return buffer.read().decode("utf-8", errors="ignore"), 1

    # ── Chunking ─────────────────────────────────────────────────────────────

    @staticmethod
    def dividir_en_chunks(texto: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """
        Divide el texto en fragmentos con superposición.
        El overlap evita que el contexto quede cortado entre chunks consecutivos.
        """
        chunks = []
        start = 0
        while start < len(texto):
            chunks.append(texto[start: start + chunk_size])
            start += chunk_size - overlap
        return [c for c in chunks if c.strip()]

    # ── API pública ───────────────────────────────────────────────────────────

    @staticmethod
    def procesar(
        s3_key: str,
        file_type: str = "pdf",
        chunk_size: int = 1000,
        overlap: int = 200,
    ) -> Tuple[List[str], int]:
        """
        Descarga el archivo desde S3, extrae texto y devuelve (chunks, páginas).
        Soporta: pdf, docx, txt.
        """
        buffer = PDFService._obtener_buffer(s3_key)

        extractores = {
            "pdf":  PDFService._extraer_pdf,
            "docx": PDFService._extraer_docx,
            "txt":  PDFService._extraer_txt,
        }

        extractor = extractores.get(file_type)
        if not extractor:
            raise Exception(f"Tipo de archivo '{file_type}' no soportado")

        texto, paginas = extractor(buffer)

        if not texto.strip():
            raise Exception("No se pudo extraer texto del documento")

        return PDFService.dividir_en_chunks(texto, chunk_size, overlap), paginas
