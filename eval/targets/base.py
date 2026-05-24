"""
Target base — clase abstracta para conectarse a cada PoC.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional


class TargetResult:
    """Resultado de una consulta a un PoC."""

    def __init__(
        self,
        target_name: str,
        mode: str,
        question: str,
        answer: str,
        latency_ms: float,
        input_tokens: int = 0,
        output_tokens: int = 0,
        retrieved_chunks: list[str] | None = None,
        error: Optional[str] = None,
    ):
        self.target_name = target_name
        self.mode = mode
        self.question = question
        self.answer = answer
        self.latency_ms = latency_ms
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.retrieved_chunks = retrieved_chunks or []
        self.error = error


class Target(ABC):
    """Clase base para un PoC target."""

    def __init__(self, name: str, base_url: str, modes: list[str]):
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.modes = modes

    @abstractmethod
    async def upload_document(self, file_path: Path) -> bool:
        """Sube un documento al PoC via /ingest."""
        ...

    @abstractmethod
    async def reindex(self) -> bool:
        """Dispara /reindex si el PoC lo requiere (no automatico)."""
        ...

    @abstractmethod
    async def query(self, question: str, mode: str) -> TargetResult:
        """Ejecuta una pregunta contra el PoC en un modo especifico."""
        ...
