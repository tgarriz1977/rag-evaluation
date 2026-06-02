#!/usr/bin/env python3
"""
RAG Evaluation Runner — orquesta la evaluacion de PoCs.

Uso:
    python -m eval.runner <escenario>
    python -m eval.runner <escenario> --target lightrag,llamaindex  # filtrar targets
    python -m eval.runner <escenario> --dry-run                    # solo mostrar que se haria
"""

import sys

# Compatibilidad: Ragas espera imports viejos de Vertex AI que en langchain-community moderna no existen.
# Redireccionamos el modulo deprecado de community al paquete especializado.
try:
    import langchain_google_vertexai
    sys.modules['langchain_community.chat_models.vertexai'] = langchain_google_vertexai
except ImportError:
    pass

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
    skip_upload: bool = False,
    skip_reindex: bool = False,
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
    if not skip_upload:
        print(f"\n{'─'*60}")
        print(f"  Subiendo documentos...")
        documentos = list(escenario.docs_dir.glob("*"))
        for t in targets:
            print(f"\n  [{t.name}] Subiendo {len(documentos)} archivos...")
            for doc in documentos:
                ok = await t.upload_document(doc)
                status = "OK" if ok else "FAIL"
                print(f"    {status}: {doc.name}")
                # Dejar respirar al parser (evita sobrecargar Docling con 503)
                if t.name in ("MS GraphRAG", "LightRAG", "RAGFlow"):
                    await asyncio.sleep(2)
    else:
        print(f"\n[INFO] Saltando subida de documentos por pedido del usuario.")

    # 3. Reindex
    if not skip_reindex:
        print(f"\n{'─'*60}")
        print(f"  Reindexando...")
        for t in targets:
            ok = await t.reindex()
            status = "OK" if ok else "FAIL"
            print(f"  [{t.name}] reindex: {status}")
            
            # Si es MS GraphRAG, pausamos el script para que el usuario corra el Job en el cluster
            if t.name == "MS GraphRAG":
                print(f"\n[!] ATENCIÓN: MS GraphRAG requiere indexación manual en el cluster.")
                print(f"    Por favor, abrí otra terminal y ejecutá el Job de Kubernetes:")
                print(f"    kubectl -n graphrag-ms delete job graphrag-ms-index 2>/dev/null")
                print(f"    kubectl -n graphrag-ms create job --from=cronjob/graphrag-ms-index manual-index")
                print(f"    ")
                print(f"    Monitoreá el progreso y, una vez que el Job finalice con éxito:")
                input("    ▶ Presioná ENTER en esta terminal para continuar con las preguntas de evaluación...")
    else:
        print(f"\n[INFO] Saltando reindexacion por pedido del usuario.")

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
                
                # 4.1 Enviar trace a LangFuse si está activo
                trace_id = None
                if langfuse:
                    try:
                        trace_id = langfuse.create_trace(result, escenario.nombre)
                    except Exception as lf_err:
                        print(f"    [WARN] No se pudo registrar trace en LangFuse: {lf_err}")

                # 4.2 Evaluar con RAGAS de forma local (independiente de si falla LangFuse)
                scores = evaluar_respuesta_ragas(
                    pregunta=pregunta.pregunta,
                    respuesta=result.answer,
                    contexto=[result.answer] if result.answer else [],
                    langfuse_client=langfuse.client if langfuse else None,
                    trace_id=trace_id,
                )
                result.scores = scores
                resultados.append(result)

    # 5. Mostrar resultados
    print(f"\n{'='*60}")
    print(f"  RESULTADOS")
    print(f"{'='*60}")
    mostrar_resultados(resultados, escenario.nombre)
    mostrar_resumen(resultados)
    
    # 5.5 Guardar informe local de resultados
    try:
        guardar_informe_local(resultados, escenario_nombre)
    except Exception as e:
        print(f"    [ERROR] No se pudo guardar el informe local: {e}")

    # 6. Flush LangFuse
    if langfuse:
        print("\n  Enviando datos a LangFuse...")
        langfuse.flush()
        print(f"  Sesion: {langfuse.session_id}")
        print(f"  Dashboard: {langfuse.host}")

    print(f"\n{'='*60}")
    print(f"  Evaluacion completada: {len(resultados)} consultas")
    print(f"{'='*60}")


def guardar_informe_local(resultados: list, escenario_nombre: str):
    """Guarda un reporte Markdown y un JSON en la carpeta del escenario."""
    import json
    from datetime import datetime
    
    escenario_dir = DATASETS_DIR / escenario_nombre
    escenario_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Guardar JSON
    json_data = []
    for r in resultados:
        scores = getattr(r, "scores", {}) or {}
        json_data.append({
            "target": r.target_name,
            "mode": r.mode,
            "question": r.question,
            "answer": r.answer,
            "latency_ms": r.latency_ms,
            "scores": {
                "faithfulness": scores.get("faithfulness", 0.0),
                "answer_relevancy": scores.get("answer_relevancy", 0.0),
                "error": scores.get("error")
            },
            "error": r.error
        })
        
    json_path = escenario_dir / "resultados_evaluacion.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)
        
    # 2. Guardar Markdown
    md_path = escenario_dir / "resultados_evaluacion.md"
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    md_content = []
    md_content.append(f"# Informe de Evaluación — Escenario: {escenario_nombre}")
    md_content.append(f"Generado el: `{now}`\n")
    
    md_content.append("## Resumen Estadístico")
    md_content.append("| Target / Modo | Consultas | Errores | Latencia Promedio | Faithfulness Prom. | Relevancy Prom. |")
    md_content.append("| :--- | :---: | :---: | :---: | :---: | :---: |")
    
    # Calcular resumen
    from collections import defaultdict
    stats = defaultdict(lambda: {
        "queries": 0, "errores": 0, "latency_total": 0.0, 
        "faith_total": 0.0, "relev_total": 0.0, "valid_scores": 0
    })
    
    for r in resultados:
        key = f"{r.target_name} / {r.mode}"
        stats[key]["queries"] += 1
        stats[key]["latency_total"] += r.latency_ms
        if r.error:
            stats[key]["errores"] += 1
            
        scores = getattr(r, "scores", {}) or {}
        if scores and "error" not in scores:
            stats[key]["faith_total"] += scores.get("faithfulness", 0.0)
            stats[key]["relev_total"] += scores.get("answer_relevancy", 0.0)
            stats[key]["valid_scores"] += 1
            
    for key, s in sorted(stats.items()):
        avg_lat = s["latency_total"] / max(s["queries"], 1)
        avg_faith = s["faith_total"] / max(s["valid_scores"], 1) if s["valid_scores"] > 0 else 0.0
        avg_relev = s["relev_total"] / max(s["valid_scores"], 1) if s["valid_scores"] > 0 else 0.0
        
        md_content.append(
            f"| {key} | {s['queries']} | {s['errores']} | {avg_lat:.0f}ms | {avg_faith:.2f} | {avg_relev:.2f} |"
        )
        
    md_content.append("\n## Detalle de Consultas\n")
    
    for i, r in enumerate(resultados, 1):
        scores = getattr(r, "scores", {}) or {}
        faith = f"{scores.get('faithfulness', 0.0):.2f}" if "faithfulness" in scores and "error" not in scores else "N/A"
        relev = f"{scores.get('answer_relevancy', 0.0):.2f}" if "answer_relevancy" in scores and "error" not in scores else "N/A"
        
        md_content.append(f"### {i}. {r.question}")
        md_content.append(f"**Target / Modo:** `{r.target_name} / {r.mode}`  ")
        md_content.append(f"**Latencia:** `{r.latency_ms:.0f}ms` | **Faithfulness:** `{faith}` | **Relevancy:** `{relev}`\n")
        
        if r.error:
            md_content.append(f"> [!CAUTION]\n> **Error:** {r.error}\n")
        else:
            md_content.append(f"**Respuesta:**\n{r.answer}\n")
            
        md_content.append("---")
        
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_content))
        
    print(f"\n[OK] Informe local guardado en:")
    print(f"  - Markdown: [resultados_evaluacion.md](file://{md_path})")
    print(f"  - JSON: [resultados_evaluacion.json](file://{json_path})")


def main():
    parser = argparse.ArgumentParser(description="RAG Evaluation Runner")
    parser.add_argument("escenario", help="Nombre del escenario en datasets/<nombre>/")
    parser.add_argument("--target", help="Filtrar targets (separados por coma): lightrag,llamaindex,langchain,graphrag_ms")
    parser.add_argument("--dry-run", action="store_true", help="Solo mostrar que se ejecutaria")
    parser.add_argument("--skip-upload", action="store_true", help="Saltar la subida de documentos")
    parser.add_argument("--skip-reindex", action="store_true", help="Saltar la reindexacion")
    parser.add_argument("--no-langfuse", action="store_true", help="Desactivar el reporte a Langfuse")

    args = parser.parse_args()
    cfg = cargar_config()

    filtro = args.target.split(",") if args.target else None
    targets = crear_targets(cfg, filtro)

    if not targets:
        print("[ERROR] No hay targets para ejecutar. Verificá config.yaml o el filtro --target.")
        sys.exit(1)

    # LangFuse reporter
    langfuse = None
    if cfg.get("langfuse_ok") and not args.dry_run and not args.no_langfuse:
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
            skip_upload=args.skip_upload,
            skip_reindex=args.skip_reindex,
        )
    )


if __name__ == "__main__":
    main()
