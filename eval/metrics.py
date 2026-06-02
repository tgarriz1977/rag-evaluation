"""
Metricas — wrapper sobre RAGAS para evaluar respuestas.
"""

import yaml
from pathlib import Path
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy
from datasets import Dataset
from langfuse import Langfuse
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"

_llm = None
_embeddings = None

def _get_evaluator_models():
    global _llm, _embeddings
    if _llm is None or _embeddings is None:
        if not CONFIG_PATH.exists():
            raise FileNotFoundError(f"No se encuentra {CONFIG_PATH}")
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        
        # Cargar LLM
        llm_cfg = cfg.get("evaluator_llm", {})
        _llm = ChatOpenAI(
            model=llm_cfg.get("model"),
            api_key=llm_cfg.get("api_key"),
            base_url=llm_cfg.get("api_base"),
            temperature=0.0
        )
        
        # Cargar Embeddings
        embed_cfg = cfg.get("evaluator_embeddings", {})
        _embeddings = OpenAIEmbeddings(
            model=embed_cfg.get("model"),
            openai_api_key=llm_cfg.get("api_key"), # RAGAS requiere pasar una key
            openai_api_base=embed_cfg.get("api_base"),
        )
    return _llm, _embeddings


def evaluar_respuesta_ragas(
    pregunta: str,
    respuesta: str,
    contexto: list[str],
    langfuse_client: Langfuse | None = None,
    trace_id: str | None = None,
) -> dict:
    """
    Evalua una respuesta usando RAGAS.
    Retorna {faithfulness, answer_relevancy} con valores 0-1.

    faithfulnes: la respuesta se contradice con el contexto?
    answer_relevancy: la respuesta es relevante a la pregunta?
    """
    if not respuesta.strip():
        return {"faithfulness": 0.0, "answer_relevancy": 0.0, "error": "Respuesta vacia"}

    if not contexto or all(not c.strip() for c in contexto):
        return {"faithfulness": 0.0, "answer_relevancy": 0.0, "error": "Sin contexto"}

    try:
        dataset = Dataset.from_dict({
            "question": [pregunta],
            "answer": [respuesta],
            "contexts": [contexto],
        })

        llm, embeddings = _get_evaluator_models()
        result = evaluate(
            dataset,
            metrics=[faithfulness, answer_relevancy],
            llm=llm,
            embeddings=embeddings,
        )

        scores = {
            "faithfulness": float(result.get("faithfulness", 0)),
            "answer_relevancy": float(result.get("answer_relevancy", 0)),
        }

        # Si tenemos LangFuse, agregamos los scores al trace
        if langfuse_client and trace_id:
            langfuse_client.create_score(
                trace_id=trace_id,
                name="faithfulness",
                value=scores["faithfulness"],
            )
            langfuse_client.create_score(
                trace_id=trace_id,
                name="answer_relevancy",
                value=scores["answer_relevancy"],
            )

        return scores

    except Exception as e:
        return {"faithfulness": 0.0, "answer_relevancy": 0.0, "error": str(e)}
