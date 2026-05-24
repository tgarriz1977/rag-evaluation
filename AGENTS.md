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
