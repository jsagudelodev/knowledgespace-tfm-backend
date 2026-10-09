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
