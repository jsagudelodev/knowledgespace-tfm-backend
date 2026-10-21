from sqlalchemy.orm import Query, Session

from app.db.models.knowledge_gap import KnowledgeGap
from app.repositories.base import BaseRepository


class KnowledgeGapRepository(BaseRepository[KnowledgeGap]):
    """Acceso a las preguntas sin respuesta satisfactoria.

    A diferencia del resto de repositorios, este expone una `Query` sin
    resolver además de resultados ya materializados. El resumen y el listado
    aplican encima filtros muy distintos —estado, período, canal, asignado,
    ordenaciones por volumen— y materializar aquí obligaría a multiplicar los
    métodos o a traer filas que luego se descartan.

    El filtro por `company_id` sí queda encapsulado: es lo que garantiza el
    aislamiento, y quien llama ya no puede olvidarlo.
    """

    def __init__(self, db: Session):
        super().__init__(KnowledgeGap, db)

    def query_by_company(self, company_id: int) -> Query:
        """Consulta base de la empresa, sin resolver, para que quien llama le
        encadene sus propios filtros."""
        return self.db.query(KnowledgeGap).filter(KnowledgeGap.company_id == company_id)

    # `get_of_company` ya no se redefine aquí: desde el 20 de octubre vive en
    # `BaseRepository`, generalizada a partir de este mismo método.
