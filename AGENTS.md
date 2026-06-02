# RAG Evaluation — Contexto para el modelo

## Proyecto

Framework de evaluación comparativa de PoCs RAG usando RAGAS + LangFuse.
Repo: https://gitlab.arba.gov.ar/infraestructura/infra-ia/rags/rag-evaluation

## Cluster

Mismo cluster RKE2 que los PoCs. Los PoCs target se acceden via Ingress:
- LightRAG: `https://lightrag.test.arba.gov.ar` (repo: .../rags/lightrag-poc)
- MS GraphRAG: `https://graphrag.test.arba.gov.ar`
- LlamaIndex: `https://llamaindex.test.arba.gov.ar`
- LangChain: `https://langchain.test.arba.gov.ar`
- RAGFlow: `https://ragflow.test.arba.gov.ar` (ya corriendo)

## Servicios que usa

| Servicio | URL |
|---|---|
| LangFuse | `langfuse.test.arba.gov.ar` |
| ARBA LLM | `https://apillm.test.arba.gov.ar` (Qwen-Thinking) |

## Estructura

Ver README.md.

## Flujo de evaluacion

1. runner.py carga el escenario (docs + preguntas)
2. Sube los docs a cada PoC target
3. Hace reindex en cada PoC
4. Por cada pregunta, consulta cada PoC en cada modo disponible
5. Evalúa con RAGAS (faithfulness, answer relevancy)
6. Envía traces + scores a LangFuse
7. Muestra tabla resumen

## Config

Ver config.yaml — targets, langfuse, dataset paths.

## Notas de Diagnóstico e Infraestructura

### Endpoints del Evaluador RAGAS
* **Embeddings**: Cuando la evaluación se ejecute desde fuera del cluster (ej. localmente), se debe utilizar la URL de Ingress externa **`https://qwen-embedding.test.arba.gov.ar/v1`** en lugar del host interno del cluster (`http://qwen-embedding-svc.vllm:8000`).
* **LLM Evaluador**: Las peticiones de inferencia en `https://apillm.test.arba.gov.ar/v1` (tanto para `Arba/Qwen-Thinking` como para `Arba/Qwen-Flash`) pueden demorar significativamente o sufrir timeouts si los pods del cluster están saturados. Es posible que requieran verificar los pods de inferencia en los namespaces `vllm`/`litellm` o configurar timeouts altos.

### Indexación de MS GraphRAG
* **Requisitos del modo Drift**: Requiere explícitamente generar embeddings para los reportes de comunidad (`community_full_content`).
* **Ejecución de Indexación**: Se ejecuta de forma manual mediante el Kubernetes Job `manual-index` en el namespace `graphrag-ms`. Una vez completado, se debe ejecutar el runner con los flags `--skip-upload --skip-reindex` para evitar re-subir documentos y regenerar el índice innecesariamente.

