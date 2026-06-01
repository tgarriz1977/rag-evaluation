"""
Metricas — wrapper sobre RAGAS para evaluar respuestas.
"""

from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy
from datasets import Dataset
from langfuse import Langfuse


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

        result = evaluate(
            dataset,
            metrics=[faithfulness, answer_relevancy],
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
