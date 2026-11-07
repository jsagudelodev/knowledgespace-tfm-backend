# Bibliografía de trabajo — capítulo 9

Lista de partida para el capítulo 2 y para las citas del resto de la memoria.
Son los trabajos canónicos de lo que este proyecto implementa: nada está aquí
por rellenar una cuota.

> ✅ **Verificadas las 21 fichas el 19 de octubre**, contrastadas contra ACL
> Anthology, NeurIPS/arXiv, IEEE y los boletines oficiales (DOUE). Ninguna
> resultó inventada: autores, año y *venue* coinciden en las 21 (el recuento
> de 22 de entonces contaba dos veces las referencias legales; ver
> «Recuento»).
>
> ✅ **Las cuatro decisiones abiertas, resueltas el 20 de octubre:**
>
> - **Formato: APA 7**, confirmado. Ya estaba así redactado, no hace falta
>   reconvertir nada.
> - **Jurisdicción: solo RGPD/UE.** El TFM se evalúa en España; se descarta la
>   ficha de la Ley 1581/2012 de Colombia. El apartado 2.3 cubre únicamente el
>   marco legal europeo.
> - **Ma et al. (2.2, recuperación léxica): se cita la versión de EMNLP.**
>   Verificado contra ACL Anthology (`2023.emnlp-main.322`): el título correcto
>   es *"Query Rewriting **in** Retrieval-Augmented Large Language Models"*
>   (no "for", que era el título del *preprint*), mismos cinco autores.
>   Ficha actualizada más abajo.
> - **Hu et al., LoRA (2.2, adaptación): se cita la versión de ICLR 2022.**
>   Verificado: mismo título y mismos ocho autores que el *preprint* de arXiv,
>   publicado después como artículo de conferencia. Ficha actualizada más
>   abajo.

> 📖 **Y léelas.** La rúbrica penaliza *«la simple reproducción de texto
> generado por herramientas automáticas sin adaptación propia»*. Esta lista es
> un punto de partida para leer, no un sustituto de leer.

---

## Cómo usarla

Las **esenciales** son las que sostienen afirmaciones que ya haces en la
memoria. Si solo lees seis, que sean esas. Las demás dan contexto y ayudan a
llegar al mínimo de 15-25 referencias.

| Prioridad | Significado |
|---|---|
| ⭐ | Esencial: la memoria ya afirma algo que esta fuente respalda |
| ○ | Contexto: útil para el capítulo 2, prescindible si falta tiempo |

---

## 2.1 — Modelos y arquitecturas

| Ver. | Pri. | Referencia | Para qué la usas |
|---|---|---|---|
| ☑ | ⭐ | Vaswani, A., Shazeer, N., Parmar, N., Uszkoreit, J., Jones, L., Gomez, A. N., Kaiser, Ł., & Polosukhin, I. (2017). Attention is all you need. *Advances in Neural Information Processing Systems*, 30. | El mecanismo de atención y la arquitectura *transformer*. Es la fuente de origen. |
| ☑ | ○ | Devlin, J., Chang, M.-W., Lee, K., & Toutanova, K. (2019). BERT: Pre-training of deep bidirectional transformers for language understanding. *NAACL-HLT*. | Representaciones bidireccionales; el puente entre *transformers* y *embeddings*. |
| ☑ | ○ | Brown, T. B., et al. (2020). Language models are few-shot learners. *Advances in Neural Information Processing Systems*, 33. | Qué es un LLM y de dónde viene el aprendizaje en contexto. |
| ☑ | ○ | Ouyang, L., et al. (2022). Training language models to follow instructions with human feedback. *Advances in Neural Information Processing Systems*, 35. | Por qué un modelo moderno obedece instrucciones: sostiene que el *prompt* restrictivo funcione. |

## 2.1 — Embeddings y similitud

| Ver. | Pri. | Referencia | Para qué la usas |
|---|---|---|---|
| ☑ | ○ | Mikolov, T., Chen, K., Corrado, G., & Dean, J. (2013). Efficient estimation of word representations in vector space. *arXiv:1301.3781*. | El origen de la idea de representar significado como vector. |
| ☑ | ⭐ | Reimers, N., & Gurevych, I. (2019). Sentence-BERT: Sentence embeddings using Siamese BERT-networks. *EMNLP-IJCNLP*. | Representaciones de **frases** comparables por similitud coseno. Justifica tu apartado 3.4. |
| ☑ | ○ | Johnson, J., Douze, M., & Jégou, H. (2019). Billion-scale similarity search with GPUs. *IEEE Transactions on Big Data*. | Búsqueda por vecinos próximos a escala: el contexto de lo que hace Pinecone. |

## 2.2 — RAG

| Ver. | Pri. | Referencia | Para qué la usas |
|---|---|---|---|
| ☑ | ⭐ | Lewis, P., et al. (2020). Retrieval-augmented generation for knowledge-intensive NLP tasks. *Advances in Neural Information Processing Systems*, 33. | **El artículo que define RAG.** Sin esta cita el capítulo 2 no se sostiene. |
| ☑ | ⭐ | Gao, Y., et al. (2023). Retrieval-augmented generation for large language models: A survey. *arXiv:2312.10997*. | De aquí sale la taxonomía *Naive / Advanced / Modular* con la que clasificas tu sistema. Es la que respondería al tutor sobre «qué arquitectura RAG». |
| ☑ | ⭐ | Karpukhin, V., et al. (2020). Dense passage retrieval for open-domain question answering. *EMNLP*. | Recuperación **densa**, que es tu técnica. Justifica el apartado 3.3. |
| ☑ | ○ | Izacard, G., & Grave, E. (2021). Leveraging passage retrieval with generative models for open domain question answering. *EACL*. | Cómo se combinan varios pasajes recuperados en una sola respuesta. |

## 2.2 — Recuperación léxica, híbrida y reordenado

> Aunque **no** los implementes, necesitas citarlos: el tutor preguntó por
> ambos y la respuesta defendible es «los conozco y decidí no incluirlos».
> Eso exige referencia.

| Ver. | Pri. | Referencia | Para qué la usas |
|---|---|---|---|
| ☑ | ⭐ | Robertson, S., & Zaragoza, H. (2009). The probabilistic relevance framework: BM25 and beyond. *Foundations and Trends in Information Retrieval*, 3(4), 333-389. | BM25, el componente léxico de un RAG híbrido. |
| ☑ | ⭐ | Nogueira, R., & Cho, K. (2019). Passage re-ranking with BERT. *arXiv:1901.04085*. | El reordenado que decidiste no implementar. |

## 2.2 — Adaptación de modelos

| Ver. | Pri. | Referencia | Para qué la usas |
|---|---|---|---|
| ☑ | ⭐ | Hu, E. J., Shen, Y., Wallis, P., Allen-Zhu, Z., Li, Y., Wang, S., Wang, L., & Chen, W. (2022). LoRA: Low-rank adaptation of large language models. *International Conference on Learning Representations (ICLR)*. | *Fine-tuning* eficiente. Es la alternativa frente a la que justificas haber elegido RAG. |
| ☑ | ○ | Wei, J., et al. (2022). Chain-of-thought prompting elicits reasoning in large language models. *Advances in Neural Information Processing Systems*, 35. | Ingeniería de *prompt* como técnica de adaptación. |
| ☑ | ○ | Ma, X., Gong, Y., He, P., Zhao, H., & Duan, N. (2023). Query rewriting in retrieval-augmented large language models. *Proceedings of the 2023 Conference on Empirical Methods in Natural Language Processing (EMNLP)*, 5303–5315. | Reescritura de consulta: el marco en el que encaja tu descomposición. |

## 5 — Evaluación y alucinaciones

| Ver. | Pri. | Referencia | Para qué la usas |
|---|---|---|---|
| ☑ | ⭐ | Es, S., James, J., Espinosa-Anke, L., & Schockaert, S. (2024). RAGAS: Automated evaluation of retrieval augmented generation. *EACL (System Demonstrations)*. | Las cuatro métricas de tu apartado 5.2. **Imprescindible.** |
| ☑ | ⭐ | Ji, Z., Lee, N., Frieske, R., Yu, T., Su, D., Xu, Y., Ishii, E., Bang, Y., Madotto, A., & Fung, P. (2023). Survey of hallucination in natural language generation. *ACM Computing Surveys*, 55(12), 1-38. | Taxonomía de alucinaciones. Sostiene los **dos modos** que documentas en 5.4. |
| ☑ | ○ | Voorhees, E. M. (1999). The TREC-8 question answering track report. *TREC*. | El origen del MRR, la métrica de tu 5.2. |

## 2.3 — Marco legal

> ✅ **Decidido el 20 de octubre: solo RGPD/UE.** El TFM se evalúa en España,
> así que el marco legal europeo es el que aplica a la institución académica.
> Se descarta la ficha de la Ley 1581/2012 de Colombia.

| Ver. | Pri. | Referencia |
|---|---|---|
| ☑ | ⭐ | Reglamento (UE) 2016/679 del Parlamento Europeo y del Consejo, de 27 de abril de 2016, relativo a la protección de las personas físicas en lo que respecta al tratamiento de datos personales (RGPD). *DOUE* L 119. |
| ☑ | ○ | Reglamento (UE) 2024/1689 del Parlamento Europeo y del Consejo, por el que se establecen normas armonizadas en materia de inteligencia artificial. *DOUE* L. |

---

## Recuento

```
esenciales  ⭐   11   (incluye el RGPD)
contexto    ○    10   (incluye el AI Act)
                 ───
total            21     (requisito: 15-25)
```

> Corregido el 22 de octubre: la versión anterior de esta tabla sumaba las
> dos referencias legales una vez dentro de esenciales/contexto y otra vez
> aparte, dando 22 en vez de 21. Verificado contando las filas reales de
> este documento (21) contra las del capítulo 9 del `.docx` (21,
> transcritas correctamente) — coinciden, no falta ninguna referencia.

Llegas al mínimo sin rellenar. Si alguna no te convence al leerla, quítala:
veinte referencias leídas valen más que veinticinco citadas de oídas.

## Decisiones — todas resueltas el 20 de octubre

1. ~~Jurisdicción~~ — **resuelto: solo RGPD/UE.** Se descarta la ficha de
   Colombia.
2. ~~Formato de cita~~ — **resuelto: APA 7**, el que ya estaba redactado.
3. ~~Verificar las fichas~~ — **hecho el 19 de octubre**, contrastadas contra
   ACL Anthology, NeurIPS/arXiv, IEEE y los boletines oficiales.
4. ~~Título y *venue* de Ma et al. y de LoRA~~ — **resuelto: versión EMNLP
   para Ma et al., versión ICLR 2022 para LoRA**, ambas verificadas y con la
   ficha ya actualizada arriba.

**Pendiente de transcripción, no de decisión:** la página exacta de Ma et al.
dentro de las actas de EMNLP no quedó confirmada en la verificación —la ficha
cita el identificador de ACL Anthology (`2023.emnlp-main.322`), que es
suficiente para localizarla, pero si APA 7 exige el rango de páginas conviene
tomarlo directamente de `aclanthology.org/2023.emnlp-main.322` al transcribir
al capítulo 9, en vez de inventarlo.

**Bibliografía transcrita al capítulo 9 de la memoria:** las 21 fichas, en
APA 7, coinciden con las de este documento (ver «Recuento»).
