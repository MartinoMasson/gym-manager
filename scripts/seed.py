"""
seed.py — Datos iniciales para categorias y preguntas.

Usa UUIDs fijos (hardcodeados) para que sean idénticos
en la DB remota y local, sin importar el orden de inserción.

Ejecutar una sola vez contra la DB remota:
    python scripts/seed.py
"""

import sys
import os
import uuid
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import RemoteSession, init_db
from app.models.evaluacion import Categoria, Pregunta


# UUIDs fijos para categorías — no cambiar nunca
CAT_ARTICULACION = uuid.UUID("00000000-0000-0000-0000-000000000001")
CAT_FUERZA       = uuid.UUID("00000000-0000-0000-0000-000000000002")
CAT_INFO_MEDICA  = uuid.UUID("00000000-0000-0000-0000-000000000003")

# UUIDs fijos para preguntas — no cambiar nunca
PREGUNTAS = [
    # Articulación
    (uuid.UUID("00000000-0000-0000-0001-000000000001"), CAT_ARTICULACION, "Columna Cervical",   "radio"),
    (uuid.UUID("00000000-0000-0000-0001-000000000002"), CAT_ARTICULACION, "Columna Torácica",   "radio"),
    (uuid.UUID("00000000-0000-0000-0001-000000000003"), CAT_ARTICULACION, "Columna Lumbar",     "radio"),
    (uuid.UUID("00000000-0000-0000-0001-000000000004"), CAT_ARTICULACION, "Columna Cadera",     "radio"),
    (uuid.UUID("00000000-0000-0000-0001-000000000005"), CAT_ARTICULACION, "Cadera",             "radio"),
    (uuid.UUID("00000000-0000-0000-0001-000000000006"), CAT_ARTICULACION, "Pie",                "radio"),
    (uuid.UUID("00000000-0000-0000-0001-000000000007"), CAT_ARTICULACION, "Hombro",             "radio"),
    (uuid.UUID("00000000-0000-0000-0001-000000000008"), CAT_ARTICULACION, "Escápula",           "radio"),
    (uuid.UUID("00000000-0000-0000-0001-000000000009"), CAT_ARTICULACION, "Codo",               "radio"),
    (uuid.UUID("00000000-0000-0000-0001-000000000010"), CAT_ARTICULACION, "Muñeca",             "radio"),
    (uuid.UUID("00000000-0000-0000-0001-000000000011"), CAT_ARTICULACION, "Rodilla",            "radio"),
    (uuid.UUID("00000000-0000-0000-0001-000000000012"), CAT_ARTICULACION, "Tobillo",            "radio"),
    # Fuerza
    (uuid.UUID("00000000-0000-0000-0002-000000000001"), CAT_FUERZA, "Tracción de miembros superior", "radio"),
    (uuid.UUID("00000000-0000-0000-0002-000000000002"), CAT_FUERZA, "Tracción de miembros inferior", "radio"),
    (uuid.UUID("00000000-0000-0000-0002-000000000003"), CAT_FUERZA, "Empuje de miembros superior",   "radio"),
    (uuid.UUID("00000000-0000-0000-0002-000000000004"), CAT_FUERZA, "Empuje de miembros inferior",   "radio"),
    (uuid.UUID("00000000-0000-0000-0002-000000000005"), CAT_FUERZA, "Core y Transporte",             "radio"),
    # Info médica
    (uuid.UUID("00000000-0000-0000-0003-000000000001"), CAT_INFO_MEDICA, "Identificación de riesgos cardíacos",    "text"),
    (uuid.UUID("00000000-0000-0000-0003-000000000002"), CAT_INFO_MEDICA, "Posibilidades motoras o dificultades",   "text"),
    (uuid.UUID("00000000-0000-0000-0003-000000000003"), CAT_INFO_MEDICA, "Posibilidades o limitaciones sensoriales", "text"),
    (uuid.UUID("00000000-0000-0000-0003-000000000004"), CAT_INFO_MEDICA, "Limitaciones farmacológicas",            "text"),
    (uuid.UUID("00000000-0000-0000-0003-000000000005"), CAT_INFO_MEDICA, "Información nutricional",                "text"),
    (uuid.UUID("00000000-0000-0000-0003-000000000006"), CAT_INFO_MEDICA, "Hábitos diarios",                        "text"),
]


def seed():
    init_db()
    session = RemoteSession()

    if session.query(Categoria).count() > 0:
        print("Ya hay datos cargados.")
        session.close()
        return

    categorias = [
        Categoria(id=CAT_ARTICULACION, nombre="articulacion"),
        Categoria(id=CAT_FUERZA,       nombre="fuerza"),
        Categoria(id=CAT_INFO_MEDICA,  nombre="info_medica"),
    ]
    session.add_all(categorias)

    preguntas = [
        Pregunta(id=pid, categoria_id=cid, nombre=nombre, tipo=tipo)
        for pid, cid, nombre, tipo in PREGUNTAS
    ]
    session.add_all(preguntas)

    session.commit()
    session.close()
    print(f"Seed completado: {len(categorias)} categorías, {len(preguntas)} preguntas.")


if __name__ == "__main__":
    seed()