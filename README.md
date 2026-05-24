# RAG Evaluation — Benchmark de PoCs con RAGAS + LangFuse

Framework para evaluar y comparar múltiples PoCs RAG (LightRAG, MS GraphRAG, LlamaIndex, LangChain) sobre los mismos documentos y preguntas, usando métricas estandarizadas via RAGAS y observabilidad via LangFuse.

## Objetivo

Responder preguntas como:
- ¿Cuál PoC es más **fiel** a los documentos (menos alucinaciones)?
- ¿Cuál da las respuestas más **relevantes**?
- ¿Cuál maneja mejor **preguntas complejas** vs preguntas directas?
- ¿Cuál es más rápido / barato en tokens?

## Los 4 PoCs en detalle

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

### Tabla comparativa rápida

| Aspecto | LightRAG | MS GraphRAG | LlamaIndex | LangChain+LangGraph |
|---|---|---|---|---|
| **Enfoque** | Grafo de conocimiento | Extracción de entidades | Routing de queries | Agentes + pipelines |
| **WebUI** | ✅ Sí (React) | ❌ No | ❌ No | ❌ No |
| **Indexación** | Automática | Manual (Job) | Explícita (/reindex) | Explícita (/reindex) |
| **Memoria** | ❌ No | ❌ No | ✅ Chat | ✅ Chat |
| **Sub-preguntas** | ❌ No | ❌ No | ✅ Sí | ❌ No (pero MultiQuery) |
| **Agente** | ❌ No | ❌ No | ❌ No | ✅ LangGraph |
| **Multi-query** | ❌ No | ❌ No | ❌ No | ✅ Sí |
| **Velocidad** | Alta | Baja | Alta | Media |
| **Complejidad** | Baja | Alta | Media | Alta |
| **Mejor para...** | Exploración rápida con UI | Datasets grandes, visión global | Preguntas complejas, descomposición | Workflows agentivos, decisiones autónomas |

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
│   ├── targets/
│   │   ├── base.py            # Clase abstracta Target
│   │   ├── lightrag.py        # LightRAG client
│   │   ├── llamaindex.py      # LlamaIndex client
│   │   ├── langchain.py       # LangChain client
│   │   └── graphrag_ms.py     # MS GraphRAG client
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
