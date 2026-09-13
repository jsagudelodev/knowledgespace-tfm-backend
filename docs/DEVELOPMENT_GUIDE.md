# KnowSpace Backend - Development Guide

## Enfoque de Enseñanza/Aprendizaje

**IMPORTANTE: Este es un proyecto de aprendizaje. Actuar como profesor, no solo como implementador.**

### Cómo Trabajamos Juntos
1. **Explicar PRIMERO** - Siempre explicar el concepto/por qué antes de implementar
2. **Dictar código** - Decirle al usuario exactamente qué escribir (ubicación del archivo, código)
3. **Esperar confirmación** - El usuario escribe el código él mismo, luego confirma
4. **Explicar qué hace** - Después de la implementación, explicar el código
5. **Pasar al siguiente paso** - Solo proceder después de que el usuario confirme que entiende

### Estilo de Aprendizaje del Usuario
- "todo lo q vas hacer lo quiero entender primero" - Quiere entender antes de implementar
- Prefiere aprender haciendo (escribiendo código él mismo)
- Construir desde cero para aprender conceptos profundamente
- Usa idioma español para explicaciones

### Principios Clave
- **NUNCA escribir código sin que el usuario lo pida o confirme**
- **Siempre explicar POR QUÉ hacemos algo, no solo QUÉ**
- **Ser paciente** - Aprender toma tiempo
- **Mantener explicaciones concisas pero completas**
- **El usuario controla el ritmo** - Esperar "listo" o confirmación antes de continuar

### Cuando el Usuario Dice "no lo hagas"
Detenerse inmediatamente. El usuario dirá explícitamente si no quiere que se haga algo.

## Flujo de Desarrollo

Al crear una nueva entidad (modelo, endpoints de API), seguir este orden exacto:

### Paso 1: Crear Modelo SQLAlchemy
**Ubicación**: `app/models/{entity_name}.py`

```python
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base

class EntityName(Base):
    __tablename__ = "table_name"
    
    id = Column(Integer, primary_key=True, index=True)
    # Add fields...
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships (if any)
    # related_entity = relationship("RelatedEntity", back_populates="entity_name")
```

**Puntos Clave:**
- Heredar de `Base` (desde `app.core.database`)
- Usar `__tablename__` para especificar el nombre de la tabla
- Agregar `index=True` a campos consultados frecuentemente
- Usar `server_default=func.now()` para created_at
- Usar `onupdate=func.now()` para updated_at
- Definir relaciones con `relationship()`

### Paso 2: Crear Schemas Pydantic
**Ubicación**: `app/schemas/{entity_name}.py`

```python
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class EntityBase(BaseModel):
    # Common fields for create/update
    pass

class EntityCreate(EntityBase):
    # Fields for creating (all required fields)
    pass

class EntityUpdate(BaseModel):
    # Fields for updating (all optional)
    # field: Optional[type] = None
    pass

class EntityResponse(BaseModel):
    # Fields for response (include id, timestamps)
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
```

**Puntos Clave:**
- Usar `BaseModel` de Pydantic
- `EntityBase` contiene campos comunes
- `EntityCreate` tiene todos los campos requeridos
- `EntityUpdate` tiene todos los campos opcionales
- `EntityResponse` incluye id y timestamps
- Siempre agregar `from_attributes = True` en Config

### Paso 3: Crear Router de API
**Ubicación**: `app/api/v1/{entity_plural}/router.py`

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.models.{entity_name} import EntityName
from app.schemas.{entity_name} import EntityCreate, EntityUpdate, EntityResponse

router = APIRouter()

@router.get("/", response_model=List[EntityResponse])
def get_entities(db: Session = Depends(get_db)):
    """List all entities"""
    entities = db.query(EntityName).all()
    return entities

@router.post("/", response_model=EntityResponse)
def create_entity(entity: EntityCreate, db: Session = Depends(get_db)):
    """Create entity"""
    db_entity = EntityName(**entity.model_dump())
    db.add(db_entity)
    db.commit()
    db.refresh(db_entity)
    return db_entity

@router.get("/{entity_id}", response_model=EntityResponse)
def get_entity(entity_id: int, db: Session = Depends(get_db)):
    """Get entity by ID"""
    entity = db.query(EntityName).filter(EntityName.id == entity_id).first()
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    return entity

@router.put("/{entity_id}", response_model=EntityResponse)
def update_entity(entity_id: int, entity: EntityUpdate, db: Session = Depends(get_db)):
    """Update entity"""
    db_entity = db.query(EntityName).filter(EntityName.id == entity_id).first()
    if not db_entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    
    for key, value in entity.model_dump(exclude_unset=True).items():
        setattr(db_entity, key, value)
    
    db.commit()
    db.refresh(db_entity)
    return db_entity

@router.delete("/{entity_id}")
def delete_entity(entity_id: int, db: Session = Depends(get_db)):
    """Delete entity"""
    db_entity = db.query(EntityName).filter(EntityName.id == entity_id).first()
    if not db_entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    
    db.delete(db_entity)
    db.commit()
    return {"message": "Entity deleted successfully"}
```

**Puntos Clave:**
- Usar `APIRouter` para routing modular
- Usar `Depends(get_db)` para inyección de sesión de base de datos
- Usar `response_model` para validación automática
- Usar `model_dump()` para convertir Pydantic a dict
- Usar `exclude_unset=True` en update para solo actualizar campos proporcionados
- Siempre verificar existencia antes de update/delete
- Retornar HTTP 404 si la entidad no se encuentra

### Paso 4: Crear Estructura de Carpetas
```
app/api/v1/{entity_plural}/
├── __init__.py (vacío)
└── router.py
```

### Paso 5: Registrar Router en main.py
```python
from app.api.v1.{entity_plural}.router import router as {entity}_router

app.include_router({entity}_router, prefix="/api/v1/{entity_plural}", tags=["{entity_plural}"])
```

## Operaciones de Base de Datos

### Crear
```python
db_entity = EntityName(**data.model_dump())
db.add(db_entity)
db.commit()
db.refresh(db_entity)
```

### Leer
```python
# Todos
entities = db.query(EntityName).all()

# Filtrar
entity = db.query(EntityName).filter(EntityName.id == id).first()

# Múltiples condiciones
entity = db.query(EntityName).filter(
    EntityName.field == value,
    EntityName.other_field == other_value
).first()
```

### Actualizar
```python
# Un solo campo
entity.field = new_value

# Múltiples campos desde dict
for key, value in data.model_dump(exclude_unset=True).items():
    setattr(entity, key, value)

db.commit()
db.refresh(entity)
```

### Eliminar
```python
db.delete(entity)
db.commit()
```

## Pruebas

### Pruebas Manuales con Swagger UI
1. Iniciar servidor: `uvicorn main:app --reload --port 8002`
2. Abrir: `http://127.0.0.1:8002/docs`
3. Probar cada endpoint

### Pruebas con curl
```bash
# Listar
curl http://127.0.0.1:8002/api/v1/entities/

# Crear
curl -X POST http://127.0.0.1:8002/api/v1/entities/ \
  -H "Content-Type: application/json" \
  -d '{"field": "value"}'

# Obtener por ID
curl http://127.0.0.1:8002/api/v1/entities/1

# Actualizar
curl -X PUT http://127.0.0.1:8002/api/v1/entities/1 \
  -H "Content-Type: application/json" \
  -d '{"field": "new_value"}'

# Eliminar
curl -X DELETE http://127.0.0.1:8002/api/v1/entities/1
```

## Convenciones de Nombres

### Modelos
- Archivo: `entity_name.py` (snake_case)
- Clase: `EntityName` (PascalCase)
- Tabla: `entity_names` (plural snake_case)

### Schemas
- Archivo: `entity_name.py` (igual que el modelo)
- Clases: `EntityCreate`, `EntityUpdate`, `EntityResponse`

### Rutas de API
- Carpeta: `entity_plural/` (plural snake_case)
- Router: `router.py`
- Prefijo: `/api/v1/{entity_plural}`
- Tag: `{entity_plural}`

## Patrones Comunes

### Relaciones de Foreign Key
```python
# En modelo
company_id = Column(Integer, ForeignKey("companies.id"))
company = relationship("Company", back_populates="users")

# En schema
company_id: int
# O incluir datos anidados
company: CompanyResponse
```

### Validación
```python
# En schema
from pydantic import EmailStr, field_validator

class EntityCreate(BaseModel):
    email: EmailStr
    
    @field_validator('email')
    def validate_email(cls, v):
        if not v.endswith('@company.com'):
            raise ValueError('Email debe ser del dominio de la empresa')
        return v
```

### Paginación
```python
@router.get("/", response_model=List[EntityResponse])
def get_entities(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    entities = db.query(EntityName).offset(skip).limit(limit).all()
    return entities
```

## Variables de Entorno

Toda la configuración está en `app/core/config.py`:
- URL de base de datos: `DATABASE_URL`
- Configuración de app: `APP_NAME`, `DEBUG`, `API_V1_STR`

Las variables se cargan del archivo `.env`.

## Estructura del Proyecto
```
knowspace_backend/
├── app/
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   └── database.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── company.py
│   │   └── {entity_name}.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── company.py
│   │   └── {entity_name}.py
│   └── api/
│       ├── __init__.py
│       └── v1/
│           ├── __init__.py
│           ├── companies/
│           │   ├── __init__.py
│           │   └── router.py
│           └── {entity_plural}/
│               ├── __init__.py
│               └── router.py
├── main.py
├── requirements.txt
├── .env
└── venv/
```

## Notas Importantes

1. **Siempre usar `__init__.py`** en cada directorio para hacerlo un paquete Python
2. **Usar `from_attributes = True`** en schemas Pydantic para compatibilidad ORM
3. **Usar `exclude_unset=True`** en operaciones de update para solo actualizar campos proporcionados
4. **Siempre verificar existencia** antes de operaciones de update/delete
5. **Usar `db.refresh()`** después de commit para obtener datos actualizados (incluyendo campos auto-generados)
6. **Usar `db.rollback()`** en bloques try/except para manejar errores
7. **Probar endpoints en Swagger UI** antes de pasar a la siguiente característica
8. **Mantener modelos y schemas separados** - modelos para BD, schemas para API
