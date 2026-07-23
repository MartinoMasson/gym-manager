"""
sync.py — Sincronización de datos entre Local (SQLite) y Remota (Postgres/Neon).

Hay DOS estrategias distintas según la tabla:

1. TABLAS CON updated_at (Usuario, Profesor, Alumno):
   Sync BIDIRECCIONAL por timestamp. Se compara updated_at en cada registro
   que existe en ambos lados, y gana el más reciente. Los registros que
   existen solo en un lado se copian al otro — NUNCA se borran por ausencia.
   El "borrado" de un Alumno/Profesor es siempre un UPDATE de estado=0
   (soft delete), nunca un DELETE físico, así que se propaga como
   cualquier otro cambio.

   Esto es necesario porque la app puede correr en varias computadoras
   sin conexión simultánea: si borráramos por ausencia, cualquier registro
   creado offline en una compu se eliminaría en cuanto sincronizara,
   porque "no estaba" en el otro lado todavía.

2. RESTO DE LAS TABLAS (Entrenamiento, DetallesAlumno, Categoria, Pregunta,
   Evaluacion, RespuestaEvaluacion, cargo_de):
   Sync UNIDIRECCIONAL remoto → local, remoto siempre gana (comportamiento
   viejo). Estas tablas todavía no tienen updated_at, así que no hay forma
   de saber cuál versión es más nueva. Mientras esto no cambie, un cambio
   hecho offline en estas tablas puede perderse en el próximo sync.
   TODO: agregar updated_at a estas tablas y migrarlas al modo bidireccional.

Resiliente a cambios de esquema: si la remota tiene columnas nuevas
que la local no tiene, las agrega automáticamente antes de sincronizar.

Optimización: el fetch de datos remotos se hace en paralelo (I/O de red),
mientras que la aplicación de cambios en SQLite local es secuencial
(SQLite es single-writer, no se puede paralelizar la escritura).
"""

import re
import sqlalchemy as sa
from sqlalchemy import inspect, text
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.database import LocalSession, RemoteSession, local_engine, remote_engine
from app.models import usuario, evaluacion
import logging

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# Tablas con estrategia bidireccional (tienen updated_at)
# ─────────────────────────────────────────────

TABLAS_BIDIRECCIONALES = [
    usuario.Usuario.__table__,
    usuario.Profesor.__table__,
    usuario.Alumno.__table__,
]

# Resto de las tablas: sync viejo, unidireccional, remoto gana
TABLAS_UNIDIRECCIONALES = [
    usuario.Entrenamiento.__table__,
    usuario.DetallesAlumno.__table__,
    evaluacion.Categoria.__table__,
    evaluacion.Pregunta.__table__,
    evaluacion.Evaluacion.__table__,
    evaluacion.RespuestaEvaluacion.__table__,
    usuario.cargo_de,
]

TODAS_LAS_TABLAS = TABLAS_BIDIRECCIONALES + TABLAS_UNIDIRECCIONALES


# ─────────────────────────────────────────────
# Schema sync: propagar columnas nuevas al local
# (sin cambios respecto a la versión anterior)
# ─────────────────────────────────────────────

def _columnas_faltantes(tabla, remote_conn, local_conn):
    """
    Compara columnas de la tabla entre remota y local.
    Retorna lista de (nombre, info) que están en remota pero no en local.
    """
    try:
        remote_inspector = inspect(remote_conn)
        local_inspector = inspect(local_conn)

        nombre = tabla.name

        if nombre not in local_inspector.get_table_names():
            return []

        remote_cols = {c["name"]: c for c in remote_inspector.get_columns(nombre)}
        local_cols = {c["name"] for c in local_inspector.get_columns(nombre)}

        faltantes = []
        for col_name, col_info in remote_cols.items():
            if col_name not in local_cols:
                faltantes.append((col_name, col_info))

        return faltantes
    except Exception:
        logger.exception(f"Error al comparar columnas de la tabla '{tabla.name}'")
        return []


def _limpiar_default_postgres(default_raw):
    """
    Postgres suele devolver defaults con cast explícito, ej:
    "'activo'::character varying" — SQLite no entiende esa sintaxis.
    Esto la elimina, dejando solo el valor literal.
    """
    if default_raw is None:
        return None
    return re.sub(r"::[\w\s]+$", "", str(default_raw)).strip()


def _aplicar_columnas_faltantes(tabla, remote_conn, local_conn, verbose=True):
    """
    Para cada columna que existe en remota pero no en local,
    emite un ALTER TABLE ... ADD COLUMN en la DB local.
    """
    try:
        faltantes = _columnas_faltantes(tabla, remote_conn, local_conn)

        for col_name, col_info in faltantes:
            tipo_str = _tipo_sqlite(col_info["type"])
            nullable = col_info.get("nullable", True)
            default_raw = _limpiar_default_postgres(col_info.get("default"))

            ddl = f'ALTER TABLE "{tabla.name}" ADD COLUMN "{col_name}" {tipo_str}'
            if not nullable and default_raw is not None:
                ddl += f" DEFAULT {default_raw} NOT NULL"
            elif not nullable:
                # SQLite no permite NOT NULL sin DEFAULT en ALTER TABLE
                ddl += " DEFAULT NULL"
            elif default_raw is not None:
                ddl += f" DEFAULT {default_raw}"

            if verbose:
                print(f"[SYNC] Schema: agregando columna '{col_name}' a '{tabla.name}'")

            local_conn.execute(text(ddl))

        return len(faltantes)
    except Exception:
        logger.exception(f"Error al aplicar columnas faltantes en la tabla '{tabla.name}'")
        return 0


def _tipo_sqlite(sa_type):
    """Mapea tipos SQLAlchemy a strings SQLite."""
    type_map = {
        "INTEGER": "INTEGER",
        "BIGINT": "INTEGER",
        "SMALLINT": "INTEGER",
        "BOOLEAN": "INTEGER",
        "FLOAT": "REAL",
        "REAL": "REAL",
        "NUMERIC": "REAL",
        "DECIMAL": "REAL",
        "VARCHAR": "TEXT",
        "TEXT": "TEXT",
        "CHAR": "TEXT",
        "DATE": "TEXT",
        "DATETIME": "TEXT",
        "TIMESTAMP": "TEXT",
        "UUID": "TEXT",
        "BLOB": "BLOB",
    }
    type_name = type(sa_type).__name__.upper()
    for key, val in type_map.items():
        if key in type_name:
            return val
    return "TEXT"  # fallback seguro


# ─────────────────────────────────────────────
# Fetch remoto / local (paralelo — cada hilo abre su propia conexión)
# ─────────────────────────────────────────────

def _fetch_tabla(engine, tabla, cols_comunes):
    """
    Corre en un hilo propio. Abre su propia conexión al engine dado
    (nunca comparte Session/Connection entre hilos).
    """
    cols_to_select = [tabla.c[c] for c in cols_comunes if c in tabla.c]
    with engine.connect() as conn:
        rows = conn.execute(sa.select(*cols_to_select)).fetchall()
    col_names = [c.key for c in cols_to_select]
    datos = [dict(row._mapping) for row in rows]
    return tabla.name, datos, col_names


# ─────────────────────────────────────────────
# Utilidades comunes
# ─────────────────────────────────────────────

def _build_where(tabla, pk_cols, pk_vals):
    condicion = None
    for col, val in zip(pk_cols, pk_vals):
        cond = (tabla.c[col] == val)
        condicion = cond if condicion is None else condicion & cond
    return condicion


def _normalizar_updated_at(valor):
    """
    SQLite guarda datetime como string; Postgres devuelve datetime real.
    Normalizamos a algo comparable (string ISO) para que la comparación
    de timestamps no falle por diferencia de tipos entre motores.
    """
    if valor is None:
        return None
    if isinstance(valor, str):
        return valor
    return valor.isoformat()


# ─────────────────────────────────────────────
# ESTRATEGIA 1: Sync bidireccional por updated_at
# (Usuario, Profesor, Alumno)
# ─────────────────────────────────────────────

def _sync_bidireccional_tabla(tabla, datos_local, datos_remoto, col_names,
                               local_session, remote_conn, verbose=True):
    """
    Compara los registros de una tabla entre local y remoto usando
    updated_at. Nunca borra por ausencia — solo inserta o actualiza,
    en cualquiera de las dos direcciones.

    Retorna (subidos, bajados, actualizados_local, actualizados_remoto)
    """
    pk_cols = [c.name for c in tabla.columns if c.primary_key]

    locales = {tuple(d[c] for c in pk_cols): d for d in datos_local}
    remotos = {tuple(d[c] for c in pk_cols): d for d in datos_remoto}

    todas_las_pks = set(locales.keys()) | set(remotos.keys())

    subidos = bajados = actualizados_local = actualizados_remoto = 0

    for pk in todas_las_pks:
        loc = locales.get(pk)
        rem = remotos.get(pk)

        # Caso 1: existe solo en local -> subir a remoto
        if loc is not None and rem is None:
            remote_conn.execute(tabla.insert().values(**loc))
            subidos += 1
            continue

        # Caso 2: existe solo en remoto -> bajar a local
        if rem is not None and loc is None:
            local_session.execute(tabla.insert().values(**rem))
            bajados += 1
            continue

        # Caso 3: existe en ambos -> comparar updated_at
        if loc is not None and rem is not None:
            if loc == rem:
                continue  # sin cambios, no hacer nada

            ts_local = _normalizar_updated_at(loc.get("updated_at"))
            ts_remoto = _normalizar_updated_at(rem.get("updated_at"))

            if ts_local is None and ts_remoto is None:
                # No hay forma de saber cuál es más nuevo; gana remoto por
                # consistencia con el comportamiento anterior.
                gana_local = False
            elif ts_local is None:
                gana_local = False
            elif ts_remoto is None:
                gana_local = True
            else:
                # Empate exacto -> gana remoto (decisión acordada)
                gana_local = ts_local > ts_remoto

            condicion_pk = _build_where(tabla, pk_cols, pk)

            if gana_local:
                remote_conn.execute(tabla.update().where(condicion_pk).values(**loc))
                actualizados_remoto += 1
            else:
                local_session.execute(tabla.update().where(condicion_pk).values(**rem))
                actualizados_local += 1

    return subidos, bajados, actualizados_local, actualizados_remoto


# ─────────────────────────────────────────────
# ESTRATEGIA 2: Sync unidireccional remoto -> local (comportamiento viejo)
# ─────────────────────────────────────────────

def _aplicar_diff_local(local_session, tabla, remotos_dicts, col_names, verbose=True):
    pk_cols = [c.name for c in tabla.columns if c.primary_key]

    locales_raw = local_session.execute(
        sa.select(*[tabla.c[c] for c in col_names])
    ).fetchall()
    locales = {tuple(row._mapping[c] for c in pk_cols): dict(row._mapping) for row in locales_raw}

    remotos = {tuple(d[c] for c in pk_cols): d for d in remotos_dicts}

    insertados = eliminados = actualizados = 0

    for pk, datos_remotos in remotos.items():
        if pk not in locales:
            local_session.execute(tabla.insert().values(**datos_remotos))
            insertados += 1
        elif datos_remotos != locales[pk]:
            condicion = _build_where(tabla, pk_cols, pk)
            local_session.execute(tabla.update().where(condicion).values(**datos_remotos))
            actualizados += 1

    for pk in locales:
        if pk not in remotos:
            condicion = _build_where(tabla, pk_cols, pk)
            local_session.execute(tabla.delete().where(condicion))
            eliminados += 1

    return insertados, actualizados, eliminados


# ─────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────

def sincronizar(verbose=True):
    if RemoteSession is None:
        print("[SYNC] No hay conexión remota configurada. Saltando sync.")
        return

    inspector = inspect(local_engine)
    if not inspector.has_table(usuario.Usuario.__table__.name):
        logger.warning("Base local sin schema. Saltando sync (correr alembic upgrade head primero).")
        return

    local_session = LocalSession()

    resumen = {}

    try:
        # 1. Propagar columnas nuevas de remota → local antes de sincronizar datos
        if verbose:
            print("[SYNC] Verificando esquema...")

        cols_agregadas = 0
        with remote_engine.connect() as remote_conn, local_engine.connect() as local_conn:
            for tabla in TODAS_LAS_TABLAS:
                n = _aplicar_columnas_faltantes(tabla, remote_conn, local_conn, verbose=verbose)
                cols_agregadas += n
            if cols_agregadas:
                local_conn.commit()
                if verbose:
                    print(f"[SYNC] Schema actualizado: {cols_agregadas} columna(s) agregada(s) ✓")
            else:
                if verbose:
                    print("[SYNC] Schema al día ✓")

        # 2. Determinar columnas comunes por tabla
        cols_por_tabla = {}
        with remote_engine.connect() as remote_conn, local_engine.connect() as local_conn:
            remote_inspector = inspect(remote_conn)
            local_inspector = inspect(local_conn)
            for tabla in TODAS_LAS_TABLAS:
                remote_cols = {c["name"] for c in remote_inspector.get_columns(tabla.name)}
                local_cols = {c["name"] for c in local_inspector.get_columns(tabla.name)}
                cols_por_tabla[tabla.name] = remote_cols & local_cols

        # 3. Fetch en paralelo: remoto para todas las tablas, y ADEMÁS
        #    local para las tablas bidireccionales (necesitamos ambos lados)
        if verbose:
            print("[SYNC] Descargando datos...")

        datos_remoto_por_tabla = {}
        datos_local_por_tabla = {}

        tareas = []
        with ThreadPoolExecutor(max_workers=8) as executor:
            futuros = {}
            for tabla in TODAS_LAS_TABLAS:
                futuros[executor.submit(_fetch_tabla, remote_engine, tabla, cols_por_tabla[tabla.name])] = ("remoto", tabla)
            for tabla in TABLAS_BIDIRECCIONALES:
                futuros[executor.submit(_fetch_tabla, local_engine, tabla, cols_por_tabla[tabla.name])] = ("local", tabla)

            for futuro in as_completed(futuros):
                origen, tabla = futuros[futuro]
                try:
                    nombre, datos, col_names = futuro.result()
                    if origen == "remoto":
                        datos_remoto_por_tabla[nombre] = (datos, col_names)
                    else:
                        datos_local_por_tabla[nombre] = (datos, col_names)
                except Exception:
                    logger.exception(f"Error al descargar datos ({origen}) de '{tabla.name}'")
                    raise

        # 4. Aplicar ESTRATEGIA 1 (bidireccional) para Usuario/Profesor/Alumno
        #    Respeta orden de FK: Usuario primero, después Profesor/Alumno.
        if verbose:
            print("[SYNC] Sincronizando usuarios/profesores/alumnos (bidireccional)...")

        with remote_engine.connect() as remote_conn:
            for tabla in TABLAS_BIDIRECCIONALES:
                datos_remoto, col_names = datos_remoto_por_tabla[tabla.name]
                datos_local, _ = datos_local_por_tabla[tabla.name]

                subidos, bajados, act_local, act_remoto = _sync_bidireccional_tabla(
                    tabla, datos_local, datos_remoto, col_names,
                    local_session, remote_conn, verbose=verbose
                )
                resumen[tabla.name] = {
                    "subidos_a_remoto": subidos,
                    "bajados_a_local": bajados,
                    "actualizados_en_local": act_local,
                    "actualizados_en_remoto": act_remoto,
                }
                if verbose:
                    print(f"[SYNC] {tabla.name}: subidos={subidos} bajados={bajados} "
                          f"act_local={act_local} act_remoto={act_remoto}")
            remote_conn.commit()

        # 5. Aplicar ESTRATEGIA 2 (unidireccional, remoto gana) para el resto
        if verbose:
            print("[SYNC] Sincronizando el resto de las tablas (remoto → local)...")

        for tabla in TABLAS_UNIDIRECCIONALES:
            datos, col_names = datos_remoto_por_tabla[tabla.name]
            i, a, e = _aplicar_diff_local(local_session, tabla, datos, col_names, verbose)
            resumen[tabla.name] = {"insertados": i, "actualizados": a, "eliminados": e}
            if verbose:
                print(f"[SYNC] {tabla.name}: +{i} actualizados={a} -{e}")

        local_session.commit()
        if verbose:
            print("[SYNC] Sincronización completada ✓")

    except Exception:
        local_session.rollback()
        logger.exception("[SYNC] Error durante la sincronización")
        raise

    finally:
        local_session.close()

    return resumen