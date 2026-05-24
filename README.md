# RAG Evaluation — Benchmark de PoCs con RAGAS + LangFuse

Framework para evaluar y comparar múltiples PoCs RAG (LightRAG, MS GraphRAG, LlamaIndex, LangChain) sobre los mismos documentos y preguntas, usando métricas estandarizadas via RAGAS y observabilidad via LangFuse.

## Objetivo

Responder preguntas como:
- ¿Cuál PoC es más **fiel** a los documentos (menos alucinaciones)?
- ¿Cuál da las respuestas más **relevantes**?
- ¿Cuál maneja mejor **preguntas complejas** vs preguntas directas?
- ¿Cuál es más rápido / barato en tokens?

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
