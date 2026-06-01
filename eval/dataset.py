"""
Dataset loader — carga escenarios desde datasets/<nombre>/
"""

import yaml
from pathlib import Path
from typing import Optional
from pydantic import BaseModel

DATASETS_DIR = Path(__file__).resolve().parent.parent / "datasets"


class Pregunta(BaseModel):
    id: str
    pregunta: str
    tipo: str  # extraccion-exacta | sumarizacion | comparacion | compleja | con-trampa
    respuesta_esperada: Optional[str] = None
    contexto: Optional[str] = None  # pista de donde encontrar la respuesta


class Escenario(BaseModel):
    nombre: str
    descripcion: str
    preguntas: list[Pregunta]
    dir_name: str

    @property
    def docs_dir(self) -> Path:
        return DATASETS_DIR / self.dir_name / "docs"


def cargar_escenario(nombre: str) -> Escenario:
    """Carga un escenario desde datasets/<nombre>/preguntas.yaml."""
    escenario_dir = DATASETS_DIR / nombre
    preguntas_path = escenario_dir / "preguntas.yaml"

    if not preguntas_path.exists():
        raise FileNotFoundError(
            f"No se encuentra {preguntas_path}. "
            f"Creá datasets/{nombre}/preguntas.yaml con las preguntas y "
            f"datasets/{nombre}/docs/ con los documentos."
        )

    with open(preguntas_path) as f:
        data = yaml.safe_load(f)

    escenario = Escenario(
        nombre=data.get("escenario", nombre),
        descripcion=data.get("descripcion", ""),
        preguntas=[Pregunta(**p) for p in data.get("preguntas", [])],
        dir_name=nombre,
    )

    print(f"  Escenario: {escenario.nombre}")
    print(f"  Documentos: {len(list(escenario.docs_dir.glob('*')))} archivos en {escenario.docs_dir}")
    print(f"  Preguntas: {len(escenario.preguntas)}")

    return escenario
