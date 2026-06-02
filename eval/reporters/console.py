"""
Console reporter — muestra resultados en tabla formateada.
"""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
from ..targets.base import TargetResult


console = Console()


def mostrar_resultados(
    resultados: list[TargetResult],
    escenario: str,
    scores: dict | None = None,
):
    """Muestra una tabla comparativa de resultados."""
    console.print()
    console.print(Panel(f"[bold blue]Resultados - {escenario}[/]", box=box.ROUNDED))
    console.print()

    # Agrupar por pregunta
    preguntas = {}
    for r in resultados:
        key = r.question[:60]
        if key not in preguntas:
            preguntas[key] = []
        preguntas[key].append(r)

    for pregunta_corta, items in preguntas.items():
        table = Table(
            title=f"[yellow]{pregunta_corta}[/]",
            box=box.SIMPLE,
            show_lines=True,
        )
        table.add_column("Target", style="cyan", no_wrap=True)
        table.add_column("Modo", style="magenta")
        table.add_column("Latencia", justify="right")
        table.add_column("Faithfulness", justify="right", style="bold yellow")
        table.add_column("Relevancy", justify="right", style="bold yellow")
        table.add_column("Respuesta (primeros 120 chars)", style="green")

        for r in items:
            status = r.error or r.answer[:120].replace("\n", " ")
            latencia = f"{r.latency_ms:.0f}ms"
            scores = getattr(r, "scores", {}) or {}
            faith = f"{scores.get('faithfulness', 0.0):.2f}" if "faithfulness" in scores and "error" not in scores else "-"
            relev = f"{scores.get('answer_relevancy', 0.0):.2f}" if "answer_relevancy" in scores and "error" not in scores else "-"
            table.add_row(r.target_name, r.mode, latencia, faith, relev, status)

        console.print(table)
        console.print()


def mostrar_resumen(resultados: list[TargetResult]):
    """Muestra resumen estadistico por target."""
    from collections import defaultdict

    stats = defaultdict(lambda: {
        "queries": 0, "errores": 0, "latencia_total": 0.0,
        "faith_total": 0.0, "relev_total": 0.0, "valid_scores": 0
    })

    for r in resultados:
        key = f"{r.target_name} / {r.mode}"
        stats[key]["queries"] += 1
        stats[key]["latencia_total"] += r.latency_ms
        if r.error:
            stats[key]["errores"] += 1
        
        scores = getattr(r, "scores", {}) or {}
        if scores and "error" not in scores:
            stats[key]["faith_total"] += scores.get("faithfulness", 0.0)
            stats[key]["relev_total"] += scores.get("answer_relevancy", 0.0)
            stats[key]["valid_scores"] += 1

    table = Table(title="[bold]Resumen por target[/]", box=box.ROUNDED)
    table.add_column("Target / Modo")
    table.add_column("Consultas", justify="right")
    table.add_column("Errores", justify="right")
    table.add_column("Lat. promedio", justify="right")
    table.add_column("Faithfulness Prom.", justify="right", style="bold yellow")
    table.add_column("Relevancy Prom.", justify="right", style="bold yellow")

    for key, s in sorted(stats.items()):
        avg_lat = s["latencia_total"] / max(s["queries"], 1)
        avg_faith = s["faith_total"] / max(s["valid_scores"], 1) if s["valid_scores"] > 0 else 0.0
        avg_relev = s["relev_total"] / max(s["valid_scores"], 1) if s["valid_scores"] > 0 else 0.0
        
        table.add_row(
            key,
            str(s["queries"]),
            str(s["errores"]),
            f"{avg_lat:.0f}ms",
            f"{avg_faith:.2f}",
            f"{avg_relev:.2f}",
        )

    console.print(table)
    console.print()
