"""Soporte de archivos .md como tipo de documento soportado — añadido el
2026-10-24. Markdown se trata como texto plano: se indexa con la sintaxis de
marcado incluida, reutilizando el mismo extractor que TXT."""
import io

from app.services.document_service import DocumentService
from app.services.pdf_service import PDFService


def test_md_es_un_tipo_de_archivo_soportado():
    assert DocumentService.validate_file_type("md") is True
    assert DocumentService.validate_file_type("MD") is True  # la extensión no distingue mayúsculas


def test_un_tipo_realmente_no_soportado_sigue_rechazado():
    """Que se haya añadido 'md' no debe aflojar la validación en general."""
    assert DocumentService.validate_file_type("exe") is False


def test_procesar_extrae_un_md_como_texto_plano(monkeypatch):
    contenido = "# Título\n\nUn párrafo con **negrita** y una lista:\n\n- uno\n- dos\n"
    monkeypatch.setattr(
        PDFService, "_obtener_buffer",
        staticmethod(lambda s3_key: io.BytesIO(contenido.encode("utf-8")))
    )

    chunks, paginas = PDFService.procesar("empresa-1/notas.md", file_type="md")

    assert paginas == 1
    texto_completo = " ".join(chunks)
    # La sintaxis de marcado se conserva tal cual: no hay un parser de
    # Markdown de por medio, es el mismo extractor que TXT.
    assert "# Título" in texto_completo
    assert "**negrita**" in texto_completo
    assert "- uno" in texto_completo
