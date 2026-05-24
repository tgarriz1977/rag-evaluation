#!/usr/bin/env python3
"""
RAG Evaluation Runner — orquesta la evaluacion de PoCs.

Uso:
    python -m eval.runner <escenario>
    python -m eval.runner <escenario> --target lightrag,llamaindex  # filtrar targets
    python -m eval.runner <escenario> --dry-run                    # solo mostrar que se haria
"""

import sys
import asyncio
import argparse
from pathlib import Path

import yaml

from .dataset import cargar_escenario, DATASETS_DIR
from .targets.generic_target import GenericTarget
from .targets.lightrag import LightRAGTarget
from .targets.ragflow import RAGFlowTarget
from .reporters.console import mostrar_resultados, mostrar_resumen
from .reporters.langfuse_reporter import LangFuseReporter
from .metrics import evaluar_respuesta_ragas

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"


def cargar_config():
    """Carga config.yaml con validacion basica."""
    path = CONFIG_PATH
    if not path.exists():
        print(f"[ERROR] No se encuentra {path}")
        print("Copiá config.yaml desde el template y completá las credenciales.")
        sys.exit(1)

    with open(path) as f:
        cfg = yaml.safe_load(f)

    # Validar LangFuse
    lf = cfg.get("langfuse", {})
    if not lf.get("public_key") or not lf.get("secret_key"):
        print("[WARN] LangFuse credenciales vacias — los resultados no se guardaran en LangFuse")
        cfg["langfuse_ok"] = False
    else:
        cfg["langfuse_ok"] = True

    return cfg


def crear_targets(cfg: dict, filtro: list[str] | None = None) -> list:
    """Crea los objetos Target segun config, opcionalmente filtrados."""
    targets_cfg = cfg.get("targets", {})
    targets = []

    for key, tcfg in targets_cfg.items():
        if filtro and key not in filtro:
            continue

        if key == "lightrag":
            t = LightRAGTarget(
                base_url=tcfg["base_url"],
                modes=tcfg["modes"],
            )
        elif key == "ragflow":
            t = RAGFlowTarget(
                base_url=tcfg["base_url"],
                modes=tcfg["modes"],
                api_key=tcfg.get("api_key", ""),
            )
        else:
            t = GenericTarget(
                name=tcfg["name"],
                base_url=tcfg["base_url"],
                modes=tcfg["modes"],
                ingest_endpoint=tcfg.get("ingest_endpoint", "/ingest"),
                reindex_endpoint=tcfg.get("reindex_endpoint"),
                query_endpoint=tcfg.get("query_endpoint", "/query"),
            )
        targets.append(t)

    return targets


async def ejecutar_escenario(
    escenario_nombre: str,
    targets: list,
    langfuse: LangFuseReporter | None,
    dry_run: bool = False,
):
    """Runner principal."""

    # 1. Cargar escenario
    print(f"\n{'='*60}")
    print(f"  Cargando escenario: {escenario_nombre}")
    print(f"{'='*60}")
    escenario = cargar_escenario(escenario_nombre)

    if dry_run:
        print(f"\n[Dry-run] Mostrando lo que se ejecutaria:")
        print(f"  Documentos a subir: {list(escenario.docs_dir.glob('*'))}")
        print(f"  Preguntas: {len(escenario.preguntas)}")
        print(f"  Targets:")
        for t in targets:
            print(f"    - {t.name} ({t.base_url}) modos: {', '.join(t.modes)}")
        print(f"  Total consultas: {len(escenario.preguntas) * sum(len(t.modes) for t in targets)}")
        return

    # 2. Subir documentos a cada target
    print(f"\n{'─'*60}")
    print(f"  Subiendo documentos...")
    documentos = list(escenario.docs_dir.glob("*"))
    for t in targets:
        print(f"\n  [{t.name}] Subiendo {len(documentos)} archivos...")
        for doc in documentos:
            ok = await t.upload_document(doc)
            status = "OK" if ok else "FAIL"
            print(f"    {status}: {doc.name}")

    # 3. Reindex
    print(f"\n{'─'*60}")
    print(f"  Reindexando...")
    for t in targets:
        ok = await t.reindex()
        status = "OK" if ok else "FAIL"
        print(f"  [{t.name}] reindex: {status}")

    # 4. Correr preguntas
    print(f"\n{'─'*60}")
    print(f"  Ejecutando preguntas...")
    resultados = []
    total = len(escenario.preguntas) * sum(len(t.modes) for t in targets)
    done = 0

    for t in targets:
        for mode in t.modes:
            for pregunta in escenario.preguntas:
                done += 1
                print(f"  [{done}/{total}] {t.name}/{mode}: {pregunta.pregunta[:50]}...")
                result = await t.query(pregunta.pregunta, mode)
                resultados.append(result)

                # Enviar a LangFuse
                if langfuse:
                    trace_id = langfuse.create_trace(result, escenario.nombre)

                    # Evaluar con RAGAS
                    scores = evaluar_respuesta_ragas(
                        pregunta=pregunta.pregunta,
                        respuesta=result.answer,
                        contexto=[result.answer] if result.answer else [],
                        langfuse_client=langfuse.client,
                        trace_id=trace_id,
                    )

    # 5. Mostrar resultados
    print(f"\n{'='*60}")
    print(f"  RESULTADOS")
    print(f"{'='*60}")
    mostrar_resultados(resultados, escenario.nombre)
    mostrar_resumen(resultados)

    # 6. Flush LangFuse
    if langfuse:
        print("\n  Enviando datos a LangFuse...")
        langfuse.flush()
        print(f"  Sesion: {langfuse.session_id}")
        print(f"  Dashboard: {langfuse.client.host}")

    print(f"\n{'='*60}")
    print(f"  Evaluacion completada: {len(resultados)} consultas")
    print(f"{'='*60}")


def main():
    parser = argparse.ArgumentParser(description="RAG Evaluation Runner")
    parser.add_argument("escenario", help="Nombre del escenario en datasets/<nombre>/")
    parser.add_argument("--target", help="Filtrar targets (separados por coma): lightrag,llamaindex,langchain,graphrag_ms")
    parser.add_argument("--dry-run", action="store_true", help="Solo mostrar que se ejecutaria")

    args = parser.parse_args()
    cfg = cargar_config()

    filtro = args.target.split(",") if args.target else None
    targets = crear_targets(cfg, filtro)

    if not targets:
        print("[ERROR] No hay targets para ejecutar. Verificá config.yaml o el filtro --target.")
        sys.exit(1)

    # LangFuse reporter
    langfuse = None
    if cfg.get("langfuse_ok") and not args.dry_run:
        lf = cfg["langfuse"]
        langfuse = LangFuseReporter(
            public_key=lf["public_key"],
            secret_key=lf["secret_key"],
            host=lf["host"],
        )

    asyncio.run(
        ejecutar_escenario(
            escenario_nombre=args.escenario,
            targets=targets,
            langfuse=langfuse,
            dry_run=args.dry_run,
        )
    )


if __name__ == "__main__":
    main()
