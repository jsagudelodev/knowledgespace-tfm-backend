# Registro de cambios

Resumen de lo hecho por sesión de trabajo. No sustituye al historial de git
—cada entrada enlaza al commit real—, sirve para encontrar rápido *qué pasó
cuándo* sin tener que leer los mensajes de commit completos.

---

## 2026-10-17

Arranca con una auditoría: ¿qué le falta al sistema para defenderse como
aplicación, al margen de la memoria? Salen tres hallazgos de código y cuatro
de pruebas manuales contra el chat real, con Langfuse de testigo.

### Configurabilidad

- **Los siete parámetros del pipeline pasan a `settings`**
  (`5cec778`). Umbral de relevancia, `top_k`, temperatura, tokens de
  respuesta, número máximo de subpreguntas, candidatos y recorte del
  reordenador: antes eran constantes de módulo —cambiar una exigía editar
  código y redesplegar—, ahora son variables de entorno con la medición que
  respalda cada valor documentada en `.env.example`. 9 tests nuevos.

### Alcance declarado

- **Ocho tablas sin modelo ORM se declaran fuera de alcance**
  (`74a353f`), no como «pendiente de implementar». Dos de ellas
  —`budget_limits`, `quota_alerts`— contienen datos obsoletos de junio de
  2026: `current_monthly_spend` marca 0,00 USD mientras `cost_tracking`
  registra consumo real. Documentado en `ALCANCE_TFM.md` y
  `docs/TFM/MODELO_DATOS.md`.

### Pruebas manuales del chat, con verificación cruzada

Se lanzaron preguntas reales contra la interfaz y se contrastó cada respuesta
contra el texto exacto de los fragmentos recuperados:

- **Un fragmento se mostraba cortado a 300 caracteres** en las fuentes del
  chat. Ante «¿qué son los hiperparámetros?», el fragmento que contenía la
  definición la tenía a partir del carácter 470: quien abriera la fuente para
  comprobar la respuesta veía un texto que no la sustentaba y podía concluir
  que el sistema había inventado. Corregido en `rag_service.py` para enviar
  el fragmento completo.
- **Una alucinación real, documentada como tercer modo**: ante «diferencias
  entre GAN y VAE», el corpus solo trata VAE en profundidad y menciona GAN de
  pasada. El sistema completó la descripción de GAN —generador,
  discriminador, proceso adversarial— con conocimiento de entrenamiento, no
  del contexto. Verificado fragmento a fragmento: ninguno de los cinco
  recuperados contiene esos términos.
- **Verificación cruzada de coste, Langfuse contra `cost_tracking`**: para
  una misma consulta, los tres componentes —generación, *embedding*,
  descomposición— coinciden al último decimal entre los dos sistemas
  ($0,000212 en ambos), confirmado además visualmente por el usuario contra
  las filas de la tabla. Documentado en `docs/TFM/OBSERVABILIDAD.md`.

### Observabilidad

- **Dos observaciones redundantes fuera de Langfuse** (`49fb57f`).
  `descomposicion` y `embedding_consulta` eran *spans* manuales que
  envolvían una llamada que el SDK ya capturaba sola como `OpenAI-generation`
  u `OpenAI-embedding` —Langfuse 4 parchea la clase `openai.OpenAI` para todo
  el proceso al importarse, no envuelve una instancia—. Cada duplicado se
  pagaba dos veces contra la cuota. Una consulta simple pasó de 7
  observaciones a 5; una compuesta, de 11 a 7. Se conservan `recuperacion` y
  `reparto`, que no son redundantes: Pinecone no se auto-instrumenta.
- **La ingesta de documentos podía quedar invisible para Langfuse**
  (`0064f2b`). `EmbeddingService` creaba su cliente con `from openai import
  OpenAI` directo y quedaba trazado solo por un efecto secundario frágil —el
  chat siempre instancia `RAGService` primero, que dispara el parche antes
  de que `EmbeddingService` construya el suyo—. Verificado en un proceso
  limpio reproduciendo el flujo real de `documents.py`: si subir un
  documento era el primer evento de un *worker*, esa llamada no dejaba
  rastro. Corregido pidiendo el cliente al mismo punto que `RAGService`. 2
  tests de regresión, comprobados contra sabotaje.

### Documentación

- `docs/TFM/OBSERVABILIDAD.md` (`6f8ee25`): verificación cruzada de coste,
  explicación del mecanismo de parcheo de Langfuse 4, estado de la ingesta
  actualizado.
- `COMO_ARRANCAR.md` y `rag_factory.py` (`910905c`): cómo elegir
  configuración y activar Langfuse; precisión del matiz del techo de
  cobertura del 50 % con `TOP_K` fijo.
- `ALCANCE_TFM.md` (`31181c8`): las cuatro configuraciones del pipeline,
  los dos niveles de mitigación de alucinaciones, Langfuse, y el recuento
  real de tests (13 archivos, 91 tests).

### Estado al cierre

```
tests           91, en verde
commits de hoy  7
```
