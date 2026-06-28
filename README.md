## Estructura del proyecto

### `.env`
Contiene las URLs de las dos bases de datos utilizadas por la aplicación:

```env
REMOTE_DATABASE_URL=postgresql://...neon.tech/gymdb?sslmode=require
LOCAL_DATABASE_URL=sqlite:///./gymmanager.db
```

### `app/database.py`
Es el corazón del proyecto. Aquí se configuran:

- Los dos motores de base de datos (SQLite local y PostgreSQL remoto).
- La clase `Base` de SQLAlchemy.
- Las sesiones (`Session`) para conectarse a las bases de datos.

El resto de la aplicación importa estas configuraciones desde este archivo.

### `app/models/`
Contiene un archivo por cada entidad del sistema. Todos los modelos heredan de `Base`.

### `migrations/env.py`
Archivo generado por Alembic que debe modificarse para:

- Importar los modelos de la aplicación.
- Leer la URL de la base de datos desde el archivo `.env`.

### `main.py`
Punto de entrada de la aplicación. Se encarga de:

- Inicializar la base de datos mediante `init_db()`.
- Levantar la interfaz gráfica con PyQt6.
- Abrir la ventana principal de la aplicación.