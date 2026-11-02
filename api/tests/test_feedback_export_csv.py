"""El CSV de "Exportar comentarios" debe abrirse bien en Excel: sin BOM, Excel
lo lee como ANSI y "Información" sale como "InformaciÃ³n". Y la fecha va en UTC
mientras la pantalla muestra hora local, así que la columna lo dice."""
from datetime import datetime, timezone
from types import SimpleNamespace

from app.repositories.feedback_repository import FeedbackRepository


def _repo_con(feedbacks):
    repo = FeedbackRepository(db=None)
    repo.get_by_company = lambda *a, **kw: feedbacks
    return repo


def test_el_csv_empieza_con_bom_utf8():
    csv = _repo_con([]).get_export_csv(company_id=8)
    assert csv.startswith("\ufeff")


def test_la_columna_de_fecha_dice_que_es_utc():
    cabecera = _repo_con([]).get_export_csv(company_id=8).lstrip("\ufeff").splitlines()[0]
    assert cabecera.split(",")[1] == "fecha_utc"


def test_las_tildes_se_conservan():
    fb = SimpleNamespace(
        id=1, created_at=datetime(2026, 11, 2, 15, 14, tzinfo=timezone.utc),
        user_full_name="Sebastián", assistant_name="Demo", rating=1,
        comment="Información desactualizada", conversation_id=7, status="new",
    )
    csv = _repo_con([fb]).get_export_csv(company_id=8)
    assert "Información desactualizada" in csv
    assert "2026-11-02 15:14" in csv
