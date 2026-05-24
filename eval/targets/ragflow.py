"""
Target para RAGFlow — usa la API REST de RAGFlow para subir documentos y consultar.

Flujo:
  1. Crea un dataset temporal via POST /api/v1/datasets
  2. Sube documentos via POST /api/v1/datasets/{dataset_id}/documents
  3. Crea un chat assistant vinculado al dataset via POST /api/v1/chats
  4. Consulta via POST /api/v1/openai/{chat_id}/chat/completions
  5. Limpia al finalizar (opcional)
"""

import time
import httpx
import uuid
from pathlib import Path
from typing import Optional

from .base import Target, TargetResult


class RAGFlowTarget(Target):
    """Target para RAGFlow — datasets + chat assistants."""

    def __init__(
        self,
        base_url: str,
        modes: list[str],
        api_key: str = "",
    ):
        super().__init__("RAGFlow", base_url, modes)
        self.api_key = api_key
        self._dataset_id: Optional[str] = None
        self._chat_id: Optional[str] = None
        self._headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}

    async def _ensure_dataset(self) -> Optional[str]:
        """Crea un dataset temporal para la evaluacion si no existe."""
        if self._dataset_id:
            return self._dataset_id

        # Generar nombre unico
        eval_id = uuid.uuid4().hex[:8]
        name = f"rag-eval-{eval_id}"

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{self.base_url}/api/v1/datasets",
                    headers=self._headers,
                    json={
                        "name": name,
                        "chunk_method": "naive",
                        "parser_config": {
                            "chunk_token_num": 512,
                            "layout_recognize": "DeepDOC",
                        },
                    },
                )
                if resp.status_code in (200, 201):
                    data = resp.json()
                    if data.get("code") == 0:
                        self._dataset_id = data["data"]["id"]
                        print(f"    [RAGFlow] Dataset creado: {self._dataset_id} ({name})")
                        return self._dataset_id
                print(f"    [WARN] RAGFlow dataset creation failed: {resp.status_code} {resp.text[:200]}")
        except Exception as e:
            print(f"    [ERROR] RAGFlow dataset creation error: {e}")
        return None

    async def _ensure_chat(self) -> Optional[str]:
        """Crea un chat assistant vinculado al dataset."""
        if self._chat_id:
            return self._chat_id

        dataset_id = await self._ensure_dataset()
        if not dataset_id:
            return None

        eval_id = uuid.uuid4().hex[:8]
        name = f"chat-eval-{eval_id}"

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{self.base_url}/api/v1/chats",
                    headers=self._headers,
                    json={
                        "name": name,
                        "dataset_ids": [dataset_id],
                        "llm": {
                            "model_name": "Arba/Qwen-Thinking",
                            "temperature": 0.1,
                        },
                        "prompt": {
                            "similarity_threshold": 0.2,
                            "vector_similarity_weight": 0.3,
                            "top_n": 5,
                        },
                    },
                )
                if resp.status_code in (200, 201):
                    data = resp.json()
                    if data.get("code") == 0:
                        self._chat_id = data["data"]["id"]
                        print(f"    [RAGFlow] Chat creado: {self._chat_id} ({name})")
                        return self._chat_id
                print(f"    [WARN] RAGFlow chat creation failed: {resp.status_code} {resp.text[:200]}")
        except Exception as e:
            print(f"    [ERROR] RAGFlow chat creation error: {e}")
        return None

    async def upload_document(self, file_path: Path) -> bool:
        dataset_id = await self._ensure_dataset()
        if not dataset_id:
            return False

        try:
            async with httpx.AsyncClient(timeout=120) as client:
                with open(file_path, "rb") as f:
                    resp = await client.post(
                        f"{self.base_url}/api/v1/datasets/{dataset_id}/documents",
                        headers=self._headers,
                        files={"file": (file_path.name, f)},
                    )
                if resp.status_code in (200, 201):
                    data = resp.json()
                    if data.get("code") == 0:
                        return True
                print(f"    [WARN] RAGFlow upload failed: {resp.status_code} {resp.text[:100]}")
                return False
        except Exception as e:
            print(f"    [ERROR] RAGFlow upload error: {e}")
            return False

    async def reindex(self) -> bool:
        # RAGFlow procesa documentos automaticamente
        # Esperar a que termine el parseo
        dataset_id = await self._ensure_dataset()
        if not dataset_id:
            return False

        # Esperar hasta 60s a que los documentos se processen
        for attempt in range(12):
            await asyncio.sleep(5)
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    resp = await client.get(
                        f"{self.base_url}/api/v1/datasets/{dataset_id}",
                        headers=self._headers,
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        if data.get("code") == 0:
                            ds = data["data"]
                            done = ds.get("done_count", 0)
                            fail = ds.get("fail_count", 0)
                            total = ds.get("document_count", 0)
                            if done + fail >= total:
                                print(f"    [RAGFlow] Documentos procesados: {done} OK, {fail} FAIL")
                                return fail == 0
            except Exception:
                pass

        print(f"    [WARN] RAGFlow reindex timeout (60s)")
        return False

    async def query(self, question: str, mode: str) -> TargetResult:
        chat_id = await self._ensure_chat()
        if not chat_id:
            return TargetResult(
                target_name="RAGFlow",
                mode=mode,
                question=question,
                answer="",
                latency_ms=0,
                error="No se pudo crear chat assistant",
            )

        url = f"{self.base_url}/api/v1/openai/{chat_id}/chat/completions"
        payload = {
            "model": "model",
            "messages": [{"role": "user", "content": question}],
            "stream": False,
        }
        start = time.time()
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.post(url, headers=self._headers, json=payload)
                elapsed = (time.time() - start) * 1000
                if resp.status_code == 200:
                    data = resp.json()
                    answer = (
                        data.get("choices", [{}])[0]
                        .get("message", {})
                        .get("content", "")
                    )
                    return TargetResult(
                        target_name="RAGFlow",
                        mode=mode,
                        question=question,
                        answer=answer,
                        latency_ms=elapsed,
                        input_tokens=data.get("usage", {}).get("prompt_tokens", 0),
                        output_tokens=data.get("usage", {}).get("completion_tokens", 0),
                    )
                else:
                    return TargetResult(
                        target_name="RAGFlow",
                        mode=mode,
                        question=question,
                        answer="",
                        latency_ms=elapsed,
                        error=f"HTTP {resp.status_code}: {resp.text[:200]}",
                    )
        except Exception as e:
            elapsed = (time.time() - start) * 1000
            return TargetResult(
                target_name="RAGFlow",
                mode=mode,
                question=question,
                answer="",
                latency_ms=elapsed,
                error=str(e),
            )

    async def cleanup(self):
        """Elimina el dataset temporal y el chat."""
        if self._chat_id:
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    await client.delete(
                        f"{self.base_url}/api/v1/chats/{self._chat_id}",
                        headers=self._headers,
                    )
            except Exception:
                pass

        if self._dataset_id:
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    await client.delete(
                        f"{self.base_url}/api/v1/datasets",
                        headers=self._headers,
                        json={"ids": [self._dataset_id]},
                    )
                print(f"    [RAGFlow] Dataset eliminado: {self._dataset_id}")
            except Exception:
                pass


# Need asyncio for sleep
import asyncio
