"""
sync.py — Sincronización unidireccional: Remota → Local
La base remota (PostgreSQL/Neon) es la fuente de verdad.

Resiliente a cambios de esquema: si la remota tiene columnas nuevas
que la local no tiene, las agrega automáticamente antes de sincronizar.
"""

import sqlalchemy as sa
from sqlalchemy import inspect, text
from app.database import LocalSession, RemoteSession, local_engine
from app.models import usuario, evaluacion


# ─────────────────────────────────────────────
# Schema sync: propagar columnas nuevas al local
# ─────────────────────────────────────────────

def _columnas_faltantes(tabla, remote_conn, local_conn):
    """
    Compara columnas de la tabla entre remota y local.
    Retorna lista de Column objects que están en remota pero no en local.
    """
    remote_inspector = inspect(remote_conn)
    local_inspector  = inspect(local_conn)

    nombre = tabla.name

    # Si la tabla directamente no existe en local, no hay nada que comparar acá
    if nombre not in local_inspector.get_table_names():
        return []

    remote_cols = {c["name"]: c for c in remote_inspector.get_columns(nombre)}
    local_cols  = {c["name"] for c in local_inspector.get_columns(nombre)}

    faltantes = []
    for col_name, col_info in remote_cols.items():
        if col_name not in local_cols:
            faltantes.append((col_name, col_info))

    return faltantes


def _aplicar_columnas_faltantes(tabla, remote_conn, local_conn, verbose=True):
    """
    Para cada columna que existe en remota pero no en local,
    emite un ALTER TABLE ... ADD COLUMN en la DB local.
    """
    faltantes = _columnas_faltantes(tabla, remote_conn, local_conn)

    for col_name, col_info in faltantes:
        tipo_str = _tipo_sqlite(col_info["type"])
        nullable = col_info.get("nullable", True)
        default  = col_info.get("default")

        ddl = f'ALTER TABLE "{tabla.name}" ADD COLUMN "{col_name}" {tipo_str}'
        if not nullable and default is not None:
            ddl += f" DEFAULT {default} NOT NULL"
        elif not nullable:
            # SQLite no permite NOT NULL sin DEFAULT en ALTER TABLE
            ddl += f" DEFAULT NULL"

        if verbose:
            print(f"[SYNC] Schema: agregando columna '{col_name}' a '{tabla.name}'")

        local_conn.execute(text(ddl))

    return len(faltantes)


def _tipo_sqlite(sa_type):
    """Mapea tipos SQLAlchemy a strings SQLite."""
    type_map = {
        "INTEGER":   "INTEGER",
        "BIGINT":    "INTEGER",
        "SMALLINT":  "INTEGER",
        "BOOLEAN":   "INTEGER",
        "FLOAT":     "REAL",
        "REAL":      "REAL",
        "NUMERIC":   "REAL",
        "DECIMAL":   "REAL",
        "VARCHAR":   "TEXT",
        "TEXT":      "TEXT",
        "CHAR":      "TEXT",
        "DATE":      "TEXT",
        "DATETIME":  "TEXT",
        "TIMESTAMP": "TEXT",
        "UUID":      "TEXT",
        "BLOB":      "BLOB",
    }
    type_name = type(sa_type).__name__.upper()
    for key, val in type_map.items():
        if key in type_name:
            return val
    return "TEXT"  # fallback seguro


# ─────────────────────────────────────────────
# Sincronización de datos
# ─────────────────────────────────────────────

def _sincronizar_tabla_raw(remote_session, local_session, tabla, verbose=True):
    nombre = tabla.name
    pk_cols = [c.name for c in tabla.columns if c.primary_key]

    # Obtener columnas que realmente existen en AMBAS DBs para esta tabla
    # (evita fallar si hay columnas en el modelo que aún no existen en alguna DB)
    remote_cols_existentes = {
        c["name"]
        for c in inspect(remote_session.bind).get_columns(nombre)
    }
    local_cols_existentes = {
        c["name"]
        for c in inspect(local_session.bind).get_columns(nombre)
    }
    cols_comunes = remote_cols_existentes & local_cols_existentes

    # Construir SELECT solo con columnas comunes
    cols_to_select = [tabla.c[c] for c in cols_comunes if c in tabla.c]

    remotos_raw = remote_session.execute(sa.select(*cols_to_select)).fetchall()
    locales_raw  = local_session.execute(sa.select(*cols_to_select)).fetchall()

    col_names = [c.key for c in cols_to_select]
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


# ─────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────

def sincronizar(verbose=True):
    if RemoteSession is None:
        print("[SYNC] No hay conexión remota configurada. Saltando sync.")
        return

    remote_session = RemoteSession()
    local_session  = LocalSession()

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

    resumen = {}

    try:
        # 1. Propagar columnas nuevas de remota → local antes de sincronizar datos
        if verbose:
            print("[SYNC] Verificando esquema...")

        cols_agregadas = 0
        with local_engine.connect() as local_conn:
            for tabla in tablas:
                n = _aplicar_columnas_faltantes(
                    tabla,
                    remote_session.bind,
                    local_conn,
                    verbose=verbose,
                )
                cols_agregadas += n
            if cols_agregadas:
                local_conn.commit()
                if verbose:
                    print(f"[SYNC] Schema actualizado: {cols_agregadas} columna(s) agregada(s) ✓")
            else:
                if verbose:
                    print("[SYNC] Schema al día ✓")

        # 2. Sincronizar datos
        for tabla in tablas:
            i, a, e = _sincronizar_tabla_raw(remote_session, local_session, tabla, verbose)
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