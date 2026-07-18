import os, sys
from logging.config import fileConfig
from sqlalchemy import create_engine, pool
from alembic import context
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils.paths import get_base_dir
load_dotenv(os.path.join(get_base_dir(), ".env"))

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

from app.database import Base

from app.models.usuario import Usuario, Profesor, Alumno, Entrenamiento, DetallesAlumno
from app.models.evaluacion import Evaluacion, Pregunta, Categoria, RespuestaEvaluacion

target_metadata = Base.metadata

LOCAL_DB_PATH = os.path.join(get_base_dir(), "gymmanager.db")
LOCAL_URL = f"sqlite:///{LOCAL_DB_PATH}"
config.set_main_option("sqlalchemy.url", LOCAL_URL)


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    x_args = context.get_x_argument(as_dictionary=True)
    target = x_args.get("db", "remote")  # default: remote

    if target == "remote":
        remote_url = os.getenv("REMOTE_DATABASE_URL")
        if not remote_url:
            raise RuntimeError("REMOTE_DATABASE_URL no está configurada; no se pueden aplicar migraciones.")
        connectable = create_engine(remote_url, poolclass=pool.NullPool)
        with connectable.connect() as connection:
            context.configure(connection=connection, target_metadata=target_metadata)
            with context.begin_transaction():
                context.run_migrations()
        connectable.dispose()

    elif target == "local":
        connectable = create_engine(LOCAL_URL, poolclass=pool.NullPool)
        with connectable.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                render_as_batch=True,
            )
            with context.begin_transaction():
                context.run_migrations()
        connectable.dispose()

    else:
        raise ValueError(f"Target desconocido: {target}")


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()