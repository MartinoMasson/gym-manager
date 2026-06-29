"""
sync.py — Sincronización unidireccional: Remota → Local
La base remota (PostgreSQL/Neon) es la fuente de verdad.
"""

from app.database import LocalSession, RemoteSession
from app.models import usuario, evaluacion


def _sincronizar_tabla_raw(remote_session, local_session, tabla):
    nombre = tabla.name
    pk_cols = [c.name for c in tabla.columns if c.primary_key]
    col_names = [c.name for c in tabla.columns]

    # ._mapping convierte cada fila en un dict accesible por nombre
    remotos_raw = remote_session.execute(tabla.select()).fetchall()
    locales_raw  = local_session.execute(tabla.select()).fetchall()

    remotos = {tuple(row._mapping[c] for c in pk_cols): dict(row._mapping) for row in remotos_raw}
    locales  = {tuple(row._mapping[c] for c in pk_cols): dict(row._mapping) for row in locales_raw}

    insertados = eliminados = actualizados = 0

    for pk, datos_remotos in remotos.items():
        if pk not in locales:
            local_session.execute(tabla.insert().values(**datos_remotos))
            insertados += 1
        else:
            if datos_remotos != locales[pk]:
                condicion = _build_where(tabla, pk_cols, pk)
                local_session.execute(tabla.update().where(condicion).values(**datos_remotos))
                actualizados += 1

    for pk in locales:
        if pk not in remotos:
            condicion = _build_where(tabla, pk_cols, pk)
            local_session.execute(tabla.delete().where(condicion))
            eliminados += 1

    return insertados, actualizados, eliminados


def _build_where(tabla, pk_cols, pk_vals):
    condicion = None
    for col, val in zip(pk_cols, pk_vals):
        cond = (tabla.c[col] == val)
        condicion = cond if condicion is None else condicion & cond
    return condicion


def sincronizar(verbose=True):
    if RemoteSession is None:
        print("[SYNC] No hay conexión remota configurada. Saltando sync.")
        return

    remote_session = RemoteSession()
    local_session = LocalSession()
    resumen = {}

    try:
        tablas = [
            usuario.Usuario.__table__,
            usuario.Profesor.__table__,
            usuario.Alumno.__table__,
            usuario.Entrenamiento.__table__,
            usuario.DetallesAlumno.__table__,
            evaluacion.Categoria.__table__,
            evaluacion.Pregunta.__table__,
            evaluacion.Evaluacion.__table__,
            evaluacion.RespuestaEvaluacion.__table__,
            usuario.cargo_de,
        ]

        for tabla in tablas:
            i, a, e = _sincronizar_tabla_raw(remote_session, local_session, tabla)
            resumen[tabla.name] = {"insertados": i, "actualizados": a, "eliminados": e}
            if verbose:
                print(f"[SYNC] {tabla.name}: +{i} actualizados={a} -{e}")

        local_session.commit()
        if verbose:
            print("[SYNC] Sincronización completada ✓")

    except Exception as ex:
        local_session.rollback()
        print(f"[SYNC] Error durante la sincronización: {ex}")
        raise

    finally:
        remote_session.close()
        local_session.close()

    return resumen