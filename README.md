# RAG Evaluation — Benchmark de PoCs con RAGAS + LangFuse

Framework para evaluar y comparar múltiples PoCs RAG (LightRAG, MS GraphRAG, LlamaIndex, LangChain, RAGFlow) sobre los mismos documentos y preguntas, usando métricas estandarizadas via RAGAS y observabilidad via LangFuse.

## Objetivo

Responder preguntas como:
- ¿Cuál PoC es más **fiel** a los documentos (menos alucinaciones)?
- ¿Cuál da las respuestas más **relevantes**?
- ¿Cuál maneja mejor **preguntas complejas** vs preguntas directas?
- ¿Cuál es más rápido / barato en tokens?

## Los 5 PoCs en detalle

### LightRAG — Knowledge Graph liviano

**Arquitectura:** Construye un grafo de conocimiento a partir de los documentos: extrae entidades, relaciones y resúmenes. Soporta 4 modos de búsqueda: local (entidades cercanas), global (vista general), hybrid (combinación) y naive (RAG clásico sin grafo).

**Ventajas:**
- ✅ Tiene **WebUI React** — se puede usar sin saber programar
- ✅ Indexación **automática** al subir documentos (no requiere /reindex manual)
- ✅ Soporte nativo de **Docling** para PDFs complejos (tablas, OCR)
- ✅ Rápido para documentos medianos (menos pasos de LLM que MS GraphRAG)
- ✅ Multiple modos de query permiten ver el mismo contenido desde distinta granularidad

**Debilidades:**
- ❌ El grafo es liviano — para datasets grandes (>500 páginas) la calidad de las relaciones baja
- ❌ No tiene **memoria conversacional** (cada query es independiente)
- ❌ No descompone preguntas complejas en sub-preguntas

**Ideal para:** Usuarios no técnicos que quieren explorar documentos con UI, o POCs rápidos donde se necesita resultados ya.

---

### Microsoft GraphRAG — Pipeline completo de extracción

**Arquitectura:** Pipeline pesado de extracción de entidades, resúmenes de comunidades y clustering. Indexa en pasos: parseo → chunking → extracción de entidades → detección de comunidades → resúmenes por comunidad. Soportes 3 modos: local (entidades), global (comunidades), drift (exploratorio).

**Ventajas:**
- ✅ **Mejor para consultas globales** sobre datasets grandes — resúmenes por comunidad dan contexto que otros no tienen
- ✅ Modo **drift** único — exploración iterativa que descubre nueva información
- ✅ Basado en la investigación de Microsoft — el más riguroso académicamente
- ✅ Bueno para responder preguntas que requieren **vista panorámica** del contenido

**Debilidades:**
- ❌ **Lento** — el indexing completo requiere muchas llamadas al LLM (puede tomar horas)
- ❌ No tiene WebUI — solo API REST
- ❌ Mayor consumo de tokens que cualquiera de los otros PoCs
- ❌ Indexing separado del serving — requiere Job + Deployment separados
- ❌ Memoria en pod solo, no persistente entre reinicios

**Ideal para:** Datasets grandes (>1000 páginas) donde se necesitan respuestas que abarquen todo el corpus, no secciones específicas.

---

### LlamaIndex — Multi-query routing

**Arquitectura:** Framework de datos para RAG que permite encadenar retrievers, índices y LLMs de forma declarativa. Este PoC ofrece 3 modos: simple (vector search clásico), subquestion (descomposición en sub-preguntas), chat (con memoria conversacional).

**Ventajas:**
- ✅ **Sub-question decomposition** — rompe preguntas complejas en partes, las responde por separado, y sintetiza
- ✅ **Memoria conversacional** — el modo chat mantiene historial entre turnos
- ✅ Más **rápido que MS GraphRAG** pero más completo que LightRAG
- ✅ Arquitectura más simple que LangChain — menos boilerplate
- ✅ Fácil de extender con nuevos retrievers o índices

**Debilidades:**
- ❌ No tiene WebUI — solo API REST
- ❌ Indexación explícita (POST /reindex) — no es automática
- ❌ No tiene capacidades agentivas — flujo lineal, no toma decisiones autónomas
- ❌ Sub-question mode puede ser costoso en llamadas LLM

**Ideal para:** Equipos técnicos que quieren un balance entre simplicidad y potencia, especialmente cuando necesitan descomposición de preguntas.

---

### LangChain + LangGraph — Agentes autónomos

**Arquitectura:** LangChain como framework de pipelines + LangGraph para grafos de estado con ciclos y decisiones. Este PoC ofrece 4 modos: simple (vector search), multi-query (genera variaciones de la pregunta), agent (StateGraph con decisión autónoma), chat (memoria conversacional).

**Ventajas:**
- ✅ **Agente autónomo** — el LangGraph StateGraph decide por sí mismo si necesita buscar documentos o responder directamente
- ✅ **MultiQueryRetriever** — genera 3-5 variaciones de la pregunta para cubrir distintos ángulos semánticos
- ✅ El más **flexible** de todos — se puede extender con herramientas, loops, ciclos condicionales
- ✅ Integración nativa con **LangFuse** via callbacks
- ✅ Ecosistema más grande — conectores para todo (SQL, APIs, vectores, etc.)

**Debilidades:**
- ❌ **Curva de aprendizaje alta** — LangGraph tiene conceptos propios (StateGraph, nodes, edges, conditional edges)
- ❌ Modo agent puede **alucinar más** si decide responder sin buscar (confianza excesiva del LLM)
- ❌ Más código boilerplate que LlamaIndex para el mismo resultado
- ❌ No tiene WebUI — solo API REST

**Ideal para:** Equipos que ya conocen LangChain y necesitan workflows agentivos complejos con toma de decisiones autónoma.

---

### RAGFlow — RAG engine todo-en-uno con agentes

**Arquitectura:** RAGFlow es un motor RAG completo que combina ingesta inteligente de documentos (DeepDoc), chunking por templates, retrieval multi-método con re-ranking, agentes con MCP, y ejecución de código en sandbox. Tiene WebUI completa + API REST compatible con OpenAI.

**Ventajas:**
- ✅ **Deep Document Understanding** — parsers especializados que entienden la estructura real del documento (tablas, imágenes, slides, Excel, PDFs escaneados)
- ✅ **Chunking por templates** — templates específicos para leyes, papers, libros, emails, presentaciones, QA, etc. (no un chunking genérico como los otros PoCs)
- ✅ **Citas trazables** — cada respuesta incluye los chunks exactos que la respaldan, reduciendo alucinaciones
- ✅ **Multiple recall + re-ranking** — combina varios métodos de recuperación con un re-ranker para mejorar precisión
- ✅ **Múltiples fuentes de datos** — no solo subida de archivos: soporta Confluence, S3, Notion, Discord, Google Drive, páginas web
- ✅ **Agentes + MCP** — sistema de agentes propio con soporte para Model Context Protocol
- ✅ **Code executor** — puede ejecutar código Python/JS en sandbox (gVisor) dentro del flujo RAG
- ✅ **WebUI completa** — interfaz web para usuarios no técnicos
- ✅ **Ya está corriendo en el cluster ARBA** — namespace `ragflow` con ElasticSearch, MinIO, MySQL, Redis

**Debilidades:**
- ❌ No tiene grafo de conocimiento (como LightRAG)
- ❌ No tiene descomposición de sub-preguntas (como LlamaIndex)
- ❌ No tiene agente con LangGraph (usa su propio sistema de agentes, menos flexible)
- ❌ API más compleja para integración programática (requiere crear dataset + chat assistant)
- ❌ Mayor consumo de recursos que PoCs más livianos (ElasticSearch, múltiples servicios)

**Ideal para:** Equipos que quieren una solución RAG completa "out of the box" con UI, chunking inteligente, y múltiples fuentes de datos sin tener que integrar componentes separados.

---

### Tabla comparativa rápida

| Aspecto | LightRAG | MS GraphRAG | LlamaIndex | LangChain+LangGraph | RAGFlow |
|---|---|---|---|---|---|---|
| **Enfoque** | Grafo de conocimiento | Extracción de entidades | Routing de queries | Agentes + pipelines | **RAG engine todo-en-uno** |
| **WebUI** | ✅ Sí (React) | ❌ No | ❌ No | ❌ No | **✅ Completa** |
| **Indexación** | Automática | Manual (Job) | Explícita (/reindex) | Explícita (/reindex) | **Automática (DeepDoc)** |
| **Memoria** | ❌ No | ❌ No | ✅ Chat | ✅ Chat | ✅ Chat |
| **Sub-preguntas** | ❌ No | ❌ No | ✅ Sí | ❌ No (pero MultiQuery) | ❌ No |
| **Agente** | ❌ No | ❌ No | ❌ No | ✅ LangGraph | **✅ Propio + MCP** |
| **Multi-query** | ❌ No | ❌ No | ❌ No | ✅ Sí | ❌ No (pero re-ranking) |
| **Chunking** | Básico | Básico | Recursivo | Recursivo | **✅ Templates + DeepDoc** |
| **Citas / Trazabilidad** | ❌ No | ❌ No | ❌ No | ❌ No | **✅ Sí** |
| **Re-ranking** | ❌ No | ❌ No | ❌ No | ❌ No | **✅ Sí** |
| **Fuentes de datos** | Subida archivos | Subida archivos | Subida archivos | Subida archivos | **✅ Confluence, S3, Notion, etc.** |
| **Code executor** | ❌ No | ❌ No | ❌ No | ❌ No | **✅ Python/JS sandbox** |
| **En cluster ARBA** | ❌ No | ❌ No | ❌ No | ❌ No | **✅ Ya corriendo** |
| **Velocidad** | Alta | Baja | Alta | Media | Media |
| **Complejidad** | Baja | Alta | Media | Alta | Media |
| **Mejor para...** | Exploración rápida con UI | Datasets grandes, visión global | Preguntas complejas, descomposición | Workflows agentivos | **Solución completa out-of-the-box** |

## Escenarios

Cada escenario = un tipo de documento + un set de preguntas.

| Escenario | Documentos | Tipos de pregunta |
|---|---|---|
| `ordenes-de-compra` | Órdenes de compra reales (PDF) | Extracción exacta, sumarización, comparación entre órdenes |
| `leyes` | Leyes / reglamentos | Artículos específicos, referencias cruzadas, interpretación |
| *(a definir)* | | |

## Cómo funciona

```
1. Configurar targets (cada PoC) en config.yaml
2. Poner los PDFs en datasets/<escenario>/docs/
3. Definir preguntas en datasets/<escenario>/preguntas.yaml
4. Correr:
   python -m eval.runner <escenario>

   El runner:
     a) Sube los docs a cada PoC via /ingest
     b) Hace /reindex en cada PoC
     c) Corre cada pregunta contra cada PoC (en todos los modos disponibles)
     d) Evalúa cada respuesta con RAGAS (faithfulness, answer relevancy)
     e) Envía todo a LangFuse con scores
     f) Muestra resumen en consola
```

### Workflow particular para MS GraphRAG

Dado que MS GraphRAG utiliza un pipeline pesado de procesamiento que se ejecuta de forma asíncrona mediante un Job de Kubernetes (`graphrag-ms-index`), el flujo para evaluarlo requiere un paso manual intermedio:

1. **Subir documentos**: Correr el runner filtrando para el target de GraphRAG para subir y convertir los archivos:
   ```bash
   .venv/bin/python -m eval.runner <escenario> --target graphrag_ms
   ```
   *Esto colocará los documentos en formato Markdown dentro de la carpeta compartida en el PVC.*

2. **Ejecutar el Job de Indexación**: Desde una terminal con acceso al cluster, disparar la indexación manual:
   ```bash
   kubectl -n graphrag-ms delete job graphrag-ms-index 2>/dev/null
   kubectl -n graphrag-ms create job --from=cronjob/graphrag-ms-index manual-index
   ```
   *Esperar a que el Job de indexación termine con éxito.*

3. **Correr la Evaluación**: Volver a correr el runner de evaluación para ejecutar la batería de preguntas, calcular métricas RAGAS e impactar en LangFuse:
   ```bash
   .venv/bin/python -m eval.runner <escenario> --target graphrag_ms
   ```

### Opciones avanzadas de optimización (Iteración rápida)

Para acelerar las pruebas repetidas y el desarrollo continuo de preguntas, el evaluador cuenta con opciones avanzadas que permiten evitar esperas innecesarias o fallos externos de red:

*   **`--skip-upload`**: Salta la etapa de subida de archivos si los documentos ya fueron cargados previamente a los targets impositivos.
*   **`--skip-reindex`**: Salta el disparo de reindexación en los PoCs (y salta la confirmación de ENTER interactiva del Job de MS GraphRAG) si el índice ya está completamente construido en el clúster.
*   **`--no-langfuse`**: Desactiva el reporte de telemetría a Langfuse. Esto es de suma utilidad si la infraestructura de red de Langfuse tiene latencias elevadas o está bajo mantenimiento técnico.

#### Ejecución sin red / Iteración local con RAGAS
Aun si utilizas `--no-langfuse`, **el evaluador calculará de manera local los scores de RAGAS** (Faithfulness y Answer Relevancy) usando tus servidores internos de inferencia. 

Para evaluar de manera instantánea reutilizando el índice y viendo los resultados directo en tu terminal, ejecuta:
```bash
.venv/bin/python -m eval.runner <escenario> --target graphrag_ms --skip-upload --skip-reindex --no-langfuse
```

#### Requisitos de Conectividad para Evaluador RAGAS (Embeddings)
Para que el evaluador local de RAGAS pueda calcular las métricas cuantitativas (`faithfulness` y `answer_relevancy`), necesita conectarse al servidor de embeddings. Tenés dos alternativas:

* **Opción A (Con Port-Forward):** Si en `config.yaml` tenés configurado `api_base: "http://localhost:8080/v1"`, debés abrir otra terminal y levantar el redireccionamiento de puertos contra el clúster:
  ```bash
  kubectl -n vllm port-forward svc/qwen3-embedding-4b-svc 8080:8000
  ```
  *Mantené esa terminal abierta durante toda la ejecución de la evaluación.*

* **Opción B (Acceso Directo por Ingress):** Podés editar el archivo `config.yaml` para apuntar directamente al endpoint externo expuesto sin necesidad de port-forward:
  ```yaml
  evaluator_embeddings:
    model: "Qwen/Qwen3-Embedding-4B"
    api_base: "https://qwen-embedding.test.arba.gov.ar/v1"
  ```

## Estructura

```
rag-evaluation/
├── config.yaml                # Targets (PoCs), LangFuse, modelos
├── datasets/
│   └── <escenario>/
│       ├── docs/              # PDFs / TXTs del escenario
│       ├── preguntas.yaml     # Preguntas + ground truth
│       └── ...                # (futuro) metadatos extra
├── eval/
│   ├── runner.py              # Orquestador principal
│   ├── dataset.py             # Carga de escenarios + preguntas
│   ├── metrics.py             # RAGAS integración
│   ├── targets/
│   │   ├── base.py            # Clase abstracta Target
│   │   ├── lightrag.py        # LightRAG client
│   │   ├── llamaindex.py      # LlamaIndex client
│   │   ├── langchain.py       # LangChain client
│   │   ├── graphrag_ms.py     # MS GraphRAG client
│   │   └── ragflow.py         # RAGFlow client (datasets + chat assistant)
│   ├── metrics.py             # RAGAS integración
│   ├── reporters/
│   │   ├── langfuse_reporter.py   # LangFuse tracing + scores
│   │   └── console.py             # Tabla resumen en terminal
│   └── dataset.py             # Carga de escenarios + preguntas
├── docker/
│   └── Dockerfile
└── requirements.txt
```

## Cómo agregar un escenario nuevo

1. Crear `datasets/<nombre>/docs/` y poner los PDFs ahí

> [!IMPORTANT]
> **Estructura Plana en `docs/`:** Los documentos deben colocarse directamente en la raíz de la carpeta `docs/` (no dentro de subcarpetas ni comprimidos en archivos `.zip`). De lo contrario, el runner del evaluador fallará al leerlos o los ignorará.

2. Crear `datasets/<nombre>/preguntas.yaml` con este formato:

```yaml
escenario: "Ordenes de Compra"
descripcion: "Evaluacion de RAGs con documentos de ordenes de compra reales"

preguntas:
  - id: "oc-001"
    pregunta: "¿Cual es el monto total de la orden OC-2024-1234?"
    tipo: extraccion-exacta
    respuesta_esperada: "$1,234,567.89"
    contexto: "Seccion de totales de la OC, generalmente al final del documento"

  - id: "oc-002"
    pregunta: "Resumi los items de la orden OC-2024-5678"
    tipo: sumarizacion
    respuesta_esperada: "La orden contiene 5 items: ..."
    contexto: "Listado completo de items de la orden"
```

3. Correr: `python -m eval.runner <nombre>`

## Requisitos

- Python 3.10+
- Acceso VPN a los endpoints de los PoCs
- API key de LangFuse (config.yaml)
- Los PoCs deployados y accesibles via HTTP
