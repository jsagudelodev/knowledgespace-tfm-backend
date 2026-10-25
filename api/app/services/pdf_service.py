"""Etapa de ingesta del pipeline RAG: extracción de texto (PDF/DOCX/TXT/MD) y
división en chunks. Los PDFs pasan por tres parsers en cascada porque ninguno
solo cubre todos los casos — ver `_extraer_pdf` y `docs/TFM/RAG_PIPELINE.md` §3."""
import io
from typing import List, Tuple

from app.core.exceptions import DocumentExtractionError
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
    - MD:   lectura directa UTF-8, igual que TXT — se indexa con la sintaxis
            de marcado incluida, sin parsear Markdown.

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
        raise DocumentExtractionError("No se pudo extraer texto del PDF con ningún parser disponible")

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
    def dividir_en_chunks_caracteres(
        texto: str, chunk_size: int = 1000, overlap: int = 200
    ) -> List[str]:
        """
        Divide por caracteres fijos (ANTIGUO).
        Rápido pero rompe oraciones a mitad.

        Usado para: compatibilidad hacia atrás, comparativas (ejercicio 6.2).
        """
        chunks = []
        start = 0
        while start < len(texto):
            chunks.append(texto[start : start + chunk_size])
            start += chunk_size - overlap
        return [c for c in chunks if c.strip()]

    @staticmethod
    def dividir_en_chunks_semantico(texto: str, target_size: int = 1000) -> List[str]:
        """
        Divide agrupando oraciones completas hasta ~target_size caracteres.

        **No recibe `overlap`, y no es un olvido.** El solapamiento existe en la
        división por caracteres para compensar que corta a ciegas: al partir
        cada 1.000 caracteres una idea queda cortada y ninguno de los dos
        fragmentos la contiene entera, así que se repiten 200 caracteres para
        que al menos uno la tenga completa. Eso se paga: la medición del
        2026-10-07 da una cobertura del 123,2 % —se indexa un 23 % de texto
        duplicado— frente al ~100 % de este método.

        Aquí ese remedio no hace falta, porque no se corta a ciegas: se corta
        donde el propio texto se corta. Por eso puede prescindir del
        solapamiento, y por eso el 0 % de cortes a mitad de palabra y el ahorro
        de volumen indexado son el mismo fenómeno visto por dos lados.

        Contrapartida medida: los fragmentos quedan menos regulares. En
        material esquemático la desviación típica de tamaño sube de 107 a 228
        caracteres, porque agrupar oraciones enteras impide ajustar cada
        fragmento al objetivo.

        Limitación conocida: `split(".")` no conserva el texto exactamente. La
        cobertura oscila entre 99,1 % y 100,4 % según el documento, es decir
        alrededor de un 1 % del contenido alterado.

        Cifras y método en `experimentos/resultados/chunking_2026-10-07.json`.
        """
        # Paso 1: divide en oraciones
        oraciones = texto.split(".")
        oraciones = [o.strip() + "." for o in oraciones if o.strip()]

        # Paso 2: agrupa oraciones hasta target_size
        chunks = []
        chunk_actual = ""
        for oracion in oraciones:
            if len(chunk_actual) + len(oracion) <= target_size:
                chunk_actual += " " + oracion
            else:
                if chunk_actual.strip():
                    chunks.append(chunk_actual)
                chunk_actual = oracion

        # Paso 3: agrega el último chunk
        if chunk_actual.strip():
            chunks.append(chunk_actual)

        return chunks

    @staticmethod
    def dividir_en_chunks(
        texto: str,
        chunk_size: int = 1000,
        overlap: int = 200,
        semantico: bool = True,
    ) -> List[str]:
        """
        Divide el texto en fragmentos. Elige automáticamente entre:
        - semantico=True  (defecto): agrupa oraciones (mejor calidad)
        - semantico=False: corta por caracteres (más rápido, compatible)

        El overlap se usa solo en modo caracteres (semántico lo ignora).
        """
        if semantico:
            return PDFService.dividir_en_chunks_semantico(texto, target_size=chunk_size)
        else:
            return PDFService.dividir_en_chunks_caracteres(texto, chunk_size, overlap)

    # ── API pública ───────────────────────────────────────────────────────────

    @staticmethod
    def procesar(
        s3_key: str,
        file_type: str = "pdf",
        chunk_size: int = 1000,
        overlap: int = 200,
        semantico: bool = True,
    ) -> Tuple[List[str], int]:
        """
        Descarga el archivo desde S3, extrae texto y devuelve (chunks, páginas).
        Soporta: pdf, docx, txt, md.

        Parámetros:
            s3_key: ruta del archivo en S3
            file_type: 'pdf', 'docx' o 'txt'
            chunk_size: tamaño aproximado de chunks (caracteres)
            overlap: superposición (solo usado en modo caracteres)
            semantico: True = agrupa oraciones (defecto, mejor calidad)
                       False = corta por caracteres (rápido, compatible)
        """
        buffer = PDFService._obtener_buffer(s3_key)

        extractores = {
            "pdf":  PDFService._extraer_pdf,
            "docx": PDFService._extraer_docx,
            "txt":  PDFService._extraer_txt,
            # Markdown es texto plano con sintaxis de marcado: se indexa tal
            # cual, con los `#`/`*`/etc. incluidos. No se le quita el formato
            # porque siguen siendo palabras buscables, y quitarlo exigiría un
            # parser de Markdown que esta extracción no necesita para nada más.
            "md":   PDFService._extraer_txt,
        }

        extractor = extractores.get(file_type)
        if not extractor:
            raise ValueError(f"Tipo de archivo '{file_type}' no soportado")

        texto, paginas = extractor(buffer)

        if not texto.strip():
            raise DocumentExtractionError("No se pudo extraer texto del documento")

        return (
            PDFService.dividir_en_chunks(texto, chunk_size, overlap, semantico),
            paginas,
        )
