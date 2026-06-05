"""
Metricas — wrapper sobre RAGAS para evaluar respuestas.
"""

import os
import re
import math
import typing as t
import yaml
from pathlib import Path
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy
from ragas.embeddings.base import BaseRagasEmbeddings
from datasets import Dataset
from langfuse import Langfuse
from langchain_openai import ChatOpenAI
from ragas.llms import LangchainLLMWrapper
from openai import OpenAI

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"

_llm = None
_embeddings = None


def _expand_env(value):
    """Expande ${VAR} o $VAR con variables de entorno."""
    if not isinstance(value, str):
        return value
    pattern = re.compile(r'\$\{(\w+)\}|\$(\w+)')
    def replacer(match):
        var = match.group(1) or match.group(2)
        return os.environ.get(var, match.group(0))
    return pattern.sub(replacer, value)


class _DirectEmbeddings(BaseRagasEmbeddings):
    """Embeddings RAGAS-nativos que llaman directamente al API OpenAI-compatible.
    Evita el doble-wrap de LangchainEmbeddingsWrapper que causa mismatch de dimensiones.
    """

    def __init__(self, model: str, api_key: str, base_url: str):
        super().__init__()
        self._client = OpenAI(api_key=api_key, base_url=base_url)
        self._model = model

    def embed_query(self, text: str) -> t.List[float]:
        r = self._client.embeddings.create(model=self._model, input=text)
        return r.data[0].embedding

    def embed_documents(self, texts: t.List[str]) -> t.List[t.List[float]]:
        r = self._client.embeddings.create(model=self._model, input=texts)
        return [item.embedding for item in r.data]

    async def aembed_query(self, text: str) -> t.List[float]:
        return self.embed_query(text)

    async def aembed_documents(self, texts: t.List[str]) -> t.List[t.List[float]]:
        return self.embed_documents(texts)


def _get_evaluator_models():
    global _llm, _embeddings
    if _llm is None or _embeddings is None:
        if not CONFIG_PATH.exists():
            raise FileNotFoundError(f"No se encuentra {CONFIG_PATH}")
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)

        # Cargar LLM
        llm_cfg = cfg.get("evaluator_llm", {})
        api_key = _expand_env(llm_cfg.get("api_key", "dummy-key"))
        os.environ["OPENAI_API_KEY"] = api_key

        _llm = LangchainLLMWrapper(ChatOpenAI(
            model=_expand_env(llm_cfg.get("model")),
            api_key=api_key,
            base_url=_expand_env(llm_cfg.get("api_base")),
            temperature=0.0
        ), bypass_n=True)

        # Cargar Embeddings via cliente directo (evita doble-wrap de langchain)
        embed_cfg = cfg.get("evaluator_embeddings", {})
        _embeddings = _DirectEmbeddings(
            model=_expand_env(embed_cfg.get("model")),
            api_key=_expand_env(embed_cfg.get("api_key", api_key)),
            base_url=_expand_env(embed_cfg.get("api_base")),
        )
    return _llm, _embeddings


def _safe_float(val_list) -> float:
    if not val_list:
        return 0.0
    try:
        val = val_list[0]
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return 0.0
        return f
    except (ValueError, TypeError, IndexError):
        return 0.0


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
        faithfulness.llm = llm
        answer_relevancy.llm = llm
        answer_relevancy.embeddings = embeddings

        result = evaluate(
            dataset,
            metrics=[faithfulness, answer_relevancy],
            llm=llm,
            embeddings=embeddings,
        )

        scores = {
            "faithfulness": _safe_float(result["faithfulness"]),
            "answer_relevancy": _safe_float(result["answer_relevancy"]),
        }

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
