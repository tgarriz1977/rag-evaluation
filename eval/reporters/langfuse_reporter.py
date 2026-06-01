"""
LangFuse reporter — crea traces por cada pregunta+modo y envia scores.
"""

from typing import Optional
from langfuse import Langfuse
from ..targets.base import TargetResult


class LangFuseReporter:
    """Maneja la conexion con LangFuse y el envio de traces."""

    def __init__(self, public_key: str, secret_key: str, host: str):
        self.client = Langfuse(
            public_key=public_key,
            secret_key=secret_key,
            host=host,
        )
        self._session_id: Optional[str] = None

    @property
    def session_id(self) -> str:
        if self._session_id is None:
            import uuid
            self._session_id = f"eval-{uuid.uuid4().hex[:8]}"
        return self._session_id

    def create_trace(self, result: TargetResult, escenario: str) -> str:
        """Crea un trace en LangFuse para una consulta y retorna el trace_id."""
        with self.client.start_as_current_observation(
            name=f"{escenario} / {result.target_name} / {result.mode}",
            input={"question": result.question, "mode": result.mode},
            output={"answer": result.answer, "error": result.error},
            metadata={
                "target": result.target_name,
                "mode": result.mode,
                "escenario": escenario,
                "latency_ms": round(result.latency_ms, 2),
                "input_tokens": result.input_tokens,
                "output_tokens": result.output_tokens,
            },
        ) as span:
            with self.client.propagate_attributes(session_id=self.session_id):
                # Score de latencia (invertido: menor latencia = mayor score)
                # Normalizacion simple: 1000ms = 0.5, 5000ms+ = 0.0
                latency_score = max(0.0, 1.0 - (result.latency_ms / 5000.0))
                span.score(name="latency", value=latency_score)

                if result.error:
                    span.score(name="error", value=0.0)

            trace_id = span.trace_id

        return trace_id

    def flush(self):
        """Espera a que todos los datos se envien a LangFuse."""
        self.client.flush()
