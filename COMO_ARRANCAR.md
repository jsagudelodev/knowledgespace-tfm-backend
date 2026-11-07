# Cómo arrancar el backend

## Requisitos

- Python 3.11+ instalado
- Archivo `api/.env` configurado con las variables reales (ver `api/.env.example`
  como referencia de qué variables existen)
- El entorno virtual del proyecto, en `api/.venv`

> **Todo se ejecuta dentro del `.venv` del proyecto, nunca con el Python del
> sistema.** El Python global de esta máquina tiene otras herramientas con
> versiones fijadas (`aider`, `langchain`) y una versión de FastAPI
> incompatible con la de `requirements.txt`. Arrancar el backend con él falla —
> ver [Problema conocido: `'FieldInfo' object has no attribute 'in_'`](#problema-conocido-fieldinfo-object-has-no-attribute-in_)
> más abajo.

## Pasos

### 1. Ubícate en la carpeta `api/`

```powershell
cd api
```

### 2. Crea el entorno virtual (solo si `api/.venv` no existe)

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Si ya existe, sáltate este paso. Solo hay que repetir la instalación cuando
cambie `requirements.txt`:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 3. Arranca el servidor

```powershell
.\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8002 --reload
```

**Qué hace cada parte:**

| Parte | Qué es |
|---|---|
| `.\.venv\Scripts\python.exe` | El intérprete **del proyecto**. Se invoca por ruta completa a propósito: así no depende de haber activado el entorno y no hay forma de usar el Python global por accidente |
| `-m uvicorn` | Ejecuta el servidor ASGI Uvicorn |
| `main:app` | Carga el objeto `app` de FastAPI desde `api/main.py` |
| `--host 127.0.0.1 --port 8002` | Dirección y puerto (`8002` es el que espera el frontend en local — ver `environment.ts` del repo frontend) |
| `--reload` | Reinicia el servidor automáticamente al detectar cambios de código (solo para desarrollo, no usar en producción) |

#### Alternativa: activar el entorno

Útil si vas a lanzar varios comandos seguidos (`pytest`, `pip`, scripts de
`experimentos/`). Una vez activado, `python` ya apunta al del proyecto:

```powershell
.\.venv\Scripts\Activate.ps1
python -m uvicorn main:app --host 127.0.0.1 --port 8002 --reload
```

Si PowerShell bloquea el script de activación, desbloquéalo **solo para esa
ventana**:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Para salir del entorno: `deactivate`.

### 4. Verifica que está funcionando

Abre en el navegador (o usa `curl`):

```
http://127.0.0.1:8002/
```

Deberías ver:

```json
{"message":"KnowledgeSpace API funcionando"}
```

### 5. Documentación interactiva de la API (Swagger)

FastAPI genera automáticamente documentación interactiva de todos los
endpoints:

```
http://127.0.0.1:8002/docs
```

## Detener el servidor

`Ctrl+C` en la terminal donde está corriendo.

---

## Elegir qué pipeline RAG atiende las consultas

La variable `RAG_CONFIGURACION` del `.env` decide qué clase responde al chat,
sin tocar código:

| Valor | Qué hace | Cuándo usarla |
|---|---|---|
| `base` | Naive RAG con filtro por umbral. La línea base de todos los experimentos | Para reproducir las mediciones del capítulo 5 tal cual |
| `descomposicion` | + descompone preguntas compuestas, sin tope de contexto | Para ver el efecto máximo de la descomposición (hasta el doble de fragmentos) |
| `reranking` | + reordena los fragmentos recuperados | Medido y **no activo por defecto**: mejora la recuperación pero no se demostró que mejoren las respuestas, y multiplica el coste por consulta — ver `rag_factory.py` |
| `descomposicion_acotada` | + descompone con tope de contexto y reparto equilibrado | **Valor por defecto.** Resuelve el mismo problema que `descomposicion` sin aumentar el presupuesto de fragmentos |
| `hibrido` | + búsqueda léxica BM25 fusionada con la densa | Medido y **no activo**: es la que mejor encuentra el fragmento correcto, pero empeora las preguntas compuestas |
| `descomposicion_hibrida` | descomposición acotada + BM25 por subpregunta | Medido y **no activo**: recupera parte de la cobertura de la híbrida sin llegar a la base, y es la más lenta |

Si el valor no coincide con ninguno de estos, el sistema avisa en el log y cae
a `base` — una variable mal escrita no debe dejar el chat sin servicio.

Para comparar configuraciones entre sí se usan los scripts de
`experimentos/`, no cambiar esta variable a mano: así cada medición queda con
su fecha y su JSON de resultados, reproducible en cualquier momento.

## Observabilidad con Langfuse (opcional)

Con `LANGFUSE_ENABLED=false` (el valor por defecto en `.env.example`) la
aplicación funciona exactamente igual, sin trazas. Para activarlas:

1. Crear un proyecto gratuito en [Langfuse Cloud](https://cloud.langfuse.com)
   (Europa) o [us.cloud.langfuse.com](https://us.cloud.langfuse.com) (Estados
   Unidos) — u otra alternativa de despliegue si prefieres levantarlo en local.
2. Copiar la clave pública y la secreta a `LANGFUSE_PUBLIC_KEY` y
   `LANGFUSE_SECRET_KEY` en `api/.env`.
3. Poner `LANGFUSE_ENABLED=true` y `LANGFUSE_HOST` acorde a la región elegida
   en el paso 1 — las dos regiones usan hosts distintos y una traza enviada a
   la región equivocada simplemente no aparece.

Con las trazas activas, cada consulta queda registrada con los fragmentos
recuperados, sus puntuaciones y las llamadas al modelo, incluidas las
auxiliares de descomposición y reordenado cuando la configuración activa las
usa. Si Langfuse falla por cualquier motivo —claves inválidas, red, servicio
caído— el chat sigue respondiendo con normalidad: la traza se pierde, nunca la
respuesta al usuario.

---

## Problema conocido: `'FieldInfo' object has no attribute 'in_'`

**Síntoma.** El servidor no llega a arrancar y la traza termina así:

```
File ".../fastapi/dependencies/utils.py", line 470, in add_param_to_fields
    if field_info.in_ == params.ParamTypes.path:
AttributeError: 'FieldInfo' object has no attribute 'in_'
```

**Causa.** Arrancaste con el Python global en vez de con el `.venv`. Las
versiones no son compatibles entre sí:

| | fastapi | pydantic |
|---|---|---|
| Python global | 0.104.1 | 2.12.5 |
| `.venv` del proyecto | 0.115.2 | 2.13.5 |

FastAPI 0.104 busca un atributo interno que las versiones modernas de Pydantic
ya no exponen. No es un fallo del código de la aplicación.

**Cómo confirmarlo.** Mira las rutas de la traza:

- `C:\Users\...\AppData\Local\Programs\Python\Python312\...` → Python global, mal
- `...\api\.venv\Lib\site-packages\...` → entorno del proyecto, bien

Para salir de dudas antes de arrancar:

```powershell
.\.venv\Scripts\python.exe -c "import sys; print(sys.prefix)"
```

Debe imprimir la ruta del `.venv`, no la de `AppData`.

**Solución.** Usar el intérprete del proyecto (paso 3). **No actualices FastAPI
en el Python global** para arreglarlo: romperías otras herramientas instaladas
ahí con versiones fijadas.

---

## Problema conocido: errores 500 intermitentes sin razón aparente

Si reinicias el backend muchas veces (cerrando la terminal en vez de usar
`Ctrl+C`, o desde varias terminales a la vez), pueden quedar **procesos
Python huérfanos** corriendo en segundo plano, todos escuchando el mismo
puerto. Windows deja que el más reciente "gane" el puerto para conexiones
nuevas, pero los viejos siguen vivos y a veces responden ellos — si tienen
cargado código desactualizado (por ejemplo, de antes de un cambio en el
modelo de datos), vas a ver errores 500 intermitentes sin razón aparente.

**Cómo diagnosticarlo (PowerShell):**
```powershell
Get-Process python | Format-Table Id, ProcessName, StartTime -AutoSize
```
Si ves más de un proceso `python` con horas de inicio distintas, ahí está
el problema.

**Cómo resolverlo:**
```powershell
Get-Process python | Stop-Process -Force
```
Y vuelve a arrancar el servidor normalmente (paso 3 de arriba). Verifica
que solo quede un proceso corriendo antes de dar por bueno un error que no
tiene explicación clara en el código.

---

## Ejecutar los tests

```powershell
cd api
.\.venv\Scripts\python.exe -m pytest
```

## Ejecutar los experimentos de la memoria

```powershell
cd api
.\.venv\Scripts\python.exe experimentos\medir_chunking.py ..\docs\Test-Documentos
```

Este experimento no llama a ningún modelo y no tiene coste, pero **sí necesita
el `.env` completo**: importar `PDFService` arrastra la configuración de la
aplicación, que exige `SECRET_KEY`, `DATABASE_URL` y las credenciales de AWS
aunque el experimento no las use.

Es solo el primero. Los comandos de todos los experimentos (EXP-01 a EXP-15),
y qué mide cada uno están en `api/experimentos/GUIA_PRUEBAS.md`;
el índice con resultados y decisiones, en `api/experimentos/REGISTRO.md`.
