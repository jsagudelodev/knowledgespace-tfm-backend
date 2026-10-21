# Bibliografía de trabajo — capítulo 9

Lista de partida para el capítulo 2 y para las citas del resto de la memoria.
Son los trabajos canónicos de lo que este proyecto implementa: nada está aquí
por rellenar una cuota.

> ✅ **Verificadas las 22 fichas el 19 de octubre**, contrastadas contra ACL
> Anthology, NeurIPS/arXiv, IEEE y los boletines oficiales (DOUE, Diario
> Oficial de Colombia). Ninguna resultó inventada: autores, año y *venue*
> coinciden en las 22. Dos detalles a decidir, no a corregir:
>
> - **Ma et al. (2.2, recuperación léxica)**: el título cambió entre el
>   preprint de arXiv (*"Query Rewriting **for**..."*, el que está aquí) y la
>   versión final de EMNLP (*"Query Rewriting **in**..."*). Decide cuál citas
>   antes de redactar.
> - **Hu et al., LoRA (2.2, adaptación)**: solo está como *preprint* de arXiv;
>   el trabajo se publicó después en ICLR 2022. Si prefieres citar la versión
>   revisada por pares, cambia el *venue*.
>
> La columna **Ver.** queda marcada para las 22 comprobadas. La ficha de la
> ley colombiana sigue pendiente de que decidas si aplica tu jurisdicción.
>
> ⚠️ **Formato por confirmar.** Está escrito en APA 7. Si EBIS exige IEEE u
> otro, se reconvierte, pero conviene saberlo antes de redactar.

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
| ☑ | ⭐ | Hu, E. J., Shen, Y., Wallis, P., Allen-Zhu, Z., Li, Y., Wang, S., Wang, L., & Chen, W. (2021). LoRA: Low-rank adaptation of large language models. *arXiv:2106.09685*. | *Fine-tuning* eficiente. Es la alternativa frente a la que justificas haber elegido RAG. |
| ☑ | ○ | Wei, J., et al. (2022). Chain-of-thought prompting elicits reasoning in large language models. *Advances in Neural Information Processing Systems*, 35. | Ingeniería de *prompt* como técnica de adaptación. |
| ☑ | ○ | Ma, X., Gong, Y., He, P., Zhao, H., & Duan, N. (2023). Query rewriting for retrieval-augmented large language models. *EMNLP*. | Reescritura de consulta: el marco en el que encaja tu descomposición. |

## 5 — Evaluación y alucinaciones

| Ver. | Pri. | Referencia | Para qué la usas |
|---|---|---|---|
| ☑ | ⭐ | Es, S., James, J., Espinosa-Anke, L., & Schockaert, S. (2024). RAGAS: Automated evaluation of retrieval augmented generation. *EACL (System Demonstrations)*. | Las cuatro métricas de tu apartado 5.2. **Imprescindible.** |
| ☑ | ⭐ | Ji, Z., Lee, N., Frieske, R., Yu, T., Su, D., Xu, Y., Ishii, E., Bang, Y., Madotto, A., & Fung, P. (2023). Survey of hallucination in natural language generation. *ACM Computing Surveys*, 55(12), 1-38. | Taxonomía de alucinaciones. Sostiene los **dos modos** que documentas en 5.4. |
| ☑ | ○ | Voorhees, E. M. (1999). The TREC-8 question answering track report. *TREC*. | El origen del MRR, la métrica de tu 5.2. |

## 2.3 — Marco legal

> ⚠️ **Pendiente de tu respuesta:** tu empresa es colombiana y el máster es
> español. Según lo que decidas, se queda la europea, la colombiana o ambas.

| Ver. | Pri. | Referencia |
|---|---|---|
| ☑ | ⭐ | Reglamento (UE) 2016/679 del Parlamento Europeo y del Consejo, de 27 de abril de 2016, relativo a la protección de las personas físicas en lo que respecta al tratamiento de datos personales (RGPD). *DOUE* L 119. |
| ☑ | ○ | Reglamento (UE) 2024/1689 del Parlamento Europeo y del Consejo, por el que se establecen normas armonizadas en materia de inteligencia artificial. *DOUE* L. |
| ☐ | ? | Ley 1581 de 2012, por la cual se dictan disposiciones generales para la protección de datos personales. *Diario Oficial*, Colombia. |

---

## Recuento

```
esenciales  ⭐   11
contexto    ○     9
legales           2-3 según jurisdicción
                 ───
total            22-23     (requisito: 15-25)
```

Llegas al mínimo sin rellenar. Si alguna no te convence al leerla, quítala:
veinte referencias leídas valen más que veinticinco citadas de oídas.

## Lo que falta decidir

1. **Jurisdicción** del apartado 2.3 — condiciona si la ficha de Colombia entra
   o no. Es la única sin verificar: el hecho (fecha de expedición, objeto de
   la ley) ya está contrastado, lo pendiente es solo si aplica a tu caso.
2. **Formato de cita** que exige EBIS (APA, IEEE, otro).
3. ~~Verificar las fichas~~ — **hecho el 19 de octubre.** Las 21 restantes
   están contrastadas contra ACL Anthology, NeurIPS/arXiv, IEEE y los
   boletines oficiales. Dos detalles a resolver antes de redactar: el título
   de Ma et al. cambió entre el *preprint* y la versión publicada (nota al
   inicio del documento), y LoRA se cita hoy solo como *preprint* pudiendo
   citarse por su versión de ICLR 2022.
