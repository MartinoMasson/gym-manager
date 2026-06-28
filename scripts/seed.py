import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import LocalSession, RemoteSession, init_db
from app.models.evaluacion import Categoria, Pregunta

def seed():
    init_db()
    session = RemoteSession()

    # Si ya hay datos no vuelve a insertar
    if session.query(Categoria).count() > 0:
        print("Ya hay datos cargados.")
        session.close()
        return

    categorias = [
        Categoria(id=1, nombre="articulacion"),
        Categoria(id=2, nombre="fuerza"),
        Categoria(id=3, nombre="info_medica"),
    ]
    session.add_all(categorias)

    preguntas = [
        Pregunta(id=1,  categoria_id=1, nombre="Columna Cervical", tipo="radio"),
        Pregunta(id=2,  categoria_id=1, nombre="Columna Torácica", tipo="radio"),
        Pregunta(id=3,  categoria_id=1, nombre="Columna Lumbar", tipo="radio"),
        Pregunta(id=4,  categoria_id=1, nombre="Columna Cadera", tipo="radio"),
        Pregunta(id=5,  categoria_id=1, nombre="Cadera", tipo="radio"),
        Pregunta(id=6,  categoria_id=1, nombre="Pie", tipo="radio"),
        Pregunta(id=7,  categoria_id=1, nombre="Hombro", tipo="radio"),
        Pregunta(id=8,  categoria_id=1, nombre="Escápula", tipo="radio"),
        Pregunta(id=9,  categoria_id=1, nombre="Codo", tipo="radio"),
        Pregunta(id=10, categoria_id=1, nombre="Muñeca", tipo="radio"),
        Pregunta(id=11, categoria_id=1, nombre="Rodilla", tipo="radio"),
        Pregunta(id=12, categoria_id=1, nombre="Tobillo", tipo="radio"),
        Pregunta(id=13, categoria_id=2, nombre="Tracción de miembros superior", tipo="radio"),
        Pregunta(id=14, categoria_id=2, nombre="Tracción de miembros inferior", tipo="radio"),
        Pregunta(id=15, categoria_id=2, nombre="Empuje de miembros superior", tipo="radio"),
        Pregunta(id=16, categoria_id=2, nombre="Empuje de miembros inferior", tipo="radio"),
        Pregunta(id=17, categoria_id=2, nombre="Core y Transporte", tipo="radio"),
        Pregunta(id=18, categoria_id=3, nombre="Identificación de riesgos cardíacos", tipo="text"),
        Pregunta(id=19, categoria_id=3, nombre="Posibilidades motoras o dificultades", tipo="text"),
        Pregunta(id=20, categoria_id=3, nombre="Posibilidades o limitaciones sensoriales", tipo="text"),
        Pregunta(id=21, categoria_id=3, nombre="Limitaciones farmacológicas", tipo="text"),
        Pregunta(id=22, categoria_id=3, nombre="Información nutricional", tipo="text"),
        Pregunta(id=23, categoria_id=3, nombre="Hábitos diarios", tipo="text"),
    ]
    session.add_all(preguntas)
    session.commit()
    session.close()
    print("Seed completado.")

if __name__ == "__main__":
    seed()