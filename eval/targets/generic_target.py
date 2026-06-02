"""
Target generico para PoCs con API REST uniforme (/ingest, /reindex, /query POST JSON).
Aplica a: LlamaIndex, LangChain, MS GraphRAG.
"""

import time
import httpx
from pathlib import Path

from .base import Target, TargetResult


class GenericTarget(Target):
    """Target para PoCs con API estandar (/ingest multipart, /query POST JSON)."""

    def __init__(
        self,
        name: str,
        base_url: str,
        modes: list[str],
        ingest_endpoint: str = "/ingest",
        reindex_endpoint: str | None = "/reindex",
        query_endpoint: str = "/query",
    ):
        super().__init__(name, base_url, modes)
        self._ingest_endpoint = ingest_endpoint
        self._reindex_endpoint = reindex_endpoint
        self._query_endpoint = query_endpoint

    async def upload_document(self, file_path: Path) -> bool:
        url = f"{self.base_url}{self._ingest_endpoint}"
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                with open(file_path, "rb") as f:
                    resp = await client.post(url, files={"file": (file_path.name, f)})
                if resp.status_code in (200, 201):
                    return True
                print(f"    [WARN] {self.name} upload failed: {resp.status_code} {resp.text[:100]}")
                return False
        except Exception as e:
            print(f"    [ERROR] {self.name} upload error: {e}")
            return False

    async def reindex(self) -> bool:
        if self._reindex_endpoint is None:
            return True  # PoC indexa automaticamente
        url = f"{self.base_url}{self._reindex_endpoint}"
        try:
            async with httpx.AsyncClient(timeout=300) as client:
                resp = await client.post(url)
                return resp.status_code in (200, 201)
        except Exception as e:
            print(f"    [ERROR] {self.name} reindex error: {e}")
            return False

    async def query(self, question: str, mode: str) -> TargetResult:
        url = f"{self.base_url}{self._query_endpoint}"
        payload = {"query": question, "mode": mode}
        start = time.time()
        try:
            async with httpx.AsyncClient(timeout=600) as client:
                resp = await client.post(url, json=payload)
                elapsed = (time.time() - start) * 1000
                if resp.status_code == 200:
                    data = resp.json()
                    return TargetResult(
                        target_name=self.name,
                        mode=mode,
                        question=question,
                        answer=data.get("answer", str(data)),
                        latency_ms=elapsed,
                    )
                else:
                    return TargetResult(
                        target_name=self.name,
                        mode=mode,
                        question=question,
                        answer="",
                        latency_ms=elapsed,
                        error=f"HTTP {resp.status_code}: {resp.text[:200]}",
                    )
        except Exception as e:
            elapsed = (time.time() - start) * 1000
            return TargetResult(
                target_name=self.name,
                mode=mode,
                question=question,
                answer="",
                latency_ms=elapsed,
                error=str(e),
            )
