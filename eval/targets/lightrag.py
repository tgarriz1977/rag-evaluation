"""
Target especifico para LightRAG (tiene endpoint de subida diferente).
"""

import time
import httpx
from pathlib import Path
from .base import Target, TargetResult


class LightRAGTarget(Target):
    """LightRAG — subida via /documents/file, query via POST /query, indexa automaticamente."""

    def __init__(self, base_url: str, modes: list[str]):
        super().__init__("LightRAG", base_url, modes)

    async def upload_document(self, file_path: Path) -> bool:
        url = f"{self.base_url}/documents/file"
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                with open(file_path, "rb") as f:
                    resp = await client.post(url, files={"file": (file_path.name, f)})
                if resp.status_code in (200, 201):
                    return True
                print(f"    [WARN] LightRAG upload failed: {resp.status_code} {resp.text[:100]}")
                return False
        except Exception as e:
            print(f"    [ERROR] LightRAG upload error: {e}")
            return False

    async def reindex(self) -> bool:
        # LightRAG indexa automaticamente al subir documentos
        return True

    async def query(self, question: str, mode: str) -> TargetResult:
        url = f"{self.base_url}/query"
        payload = {"query": question, "mode": mode}
        start = time.time()
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.post(url, json=payload)
                elapsed = (time.time() - start) * 1000
                if resp.status_code == 200:
                    data = resp.json()
                    return TargetResult(
                        target_name="LightRAG",
                        mode=mode,
                        question=question,
                        answer=data.get("response", data.get("answer", str(data))),
                        latency_ms=elapsed,
                    )
                else:
                    return TargetResult(
                        target_name="LightRAG",
                        mode=mode,
                        question=question,
                        answer="",
                        latency_ms=elapsed,
                        error=f"HTTP {resp.status_code}: {resp.text[:200]}",
                    )
        except Exception as e:
            elapsed = (time.time() - start) * 1000
            return TargetResult(
                target_name="LightRAG",
                mode=mode,
                question=question,
                answer="",
                latency_ms=elapsed,
                error=str(e),
            )
