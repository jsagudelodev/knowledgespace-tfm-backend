# Cómo arrancar el backend

## Requisitos

- Python 3.11+ instalado
- Archivo `api/.env` configurado con las variables reales (ver `api/.env.example`
  como referencia de qué variables existen)

## Pasos

### 1. Ubícate en la carpeta `api/`

```bash
cd api
```

### 2. Instala las dependencias (solo la primera vez, o si cambia `requirements.txt`)

```bash
pip install -r requirements.txt
```

### 3. Arranca el servidor

```bash
python -m uvicorn main:app --host 127.0.0.1 --port 8002 --reload
```

**Qué hace cada parte:**

| Parte | Qué es |
|---|---|
| `python -m uvicorn` | Ejecuta el servidor ASGI Uvicorn |
| `main:app` | Carga el objeto `app` de FastAPI desde `api/main.py` |
| `--host 127.0.0.1 --port 8002` | Dirección y puerto (`8002` es el que espera el frontend en local — ver `environment.ts` del repo frontend) |
| `--reload` | Reinicia el servidor automáticamente al detectar cambios de código (solo para desarrollo, no usar en producción) |

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

## Problema conocido: "No se pudieron cargar los widgets" (o errores 500 intermitentes)

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

## Ejecutar los tests

```bash
cd api
pytest
```
