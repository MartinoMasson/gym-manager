# GymManager

App de escritorio para administración de gimnasio.  
Stack: Python · PyQt6 · SQLAlchemy · Alembic · SQLite local · Neon PostgreSQL remoto.

---

## Setup inicial

```bash
# 1. Crear entorno virtual
python -m venv venv
venv\Scripts\activate

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Configurar variables de entorno
cp .env.example .env
# Editar .env con la URL de Neon

# 4. Resetear y crear tablas en DB remota
python resetdb_remote.py

# 5. Aplicar migraciones en DB local
alembic upgrade head

# 6. Cargar datos iniciales (categorías y preguntas de evaluación)
python scripts/seed.py

# 7. Correr la app
python main.py
```

---

## Estructura del proyecto

```text
gym-manager/
├── main.py                           # Entry point
├── alembic.ini                       # Configuración de Alembic
├── requirements.txt                  # Dependencias
├── resetdb_remote.py                 # Reset completo de la DB remota (solo setup inicial)
├── .env                              # Variables de entorno (no commitear)
│
├── app/
│   ├── database.py                   # SQLite + PostgreSQL, Base ORM, sesiones y get_sessions()
│   ├── state.py                      # Estado global (AppState + señales PyQt)
│   │
│   ├── jobs/
│   │   ├── scheduler.py              # Setup y lifecycle del scheduler
│   │   └── cleanup_jobs.py           # Job de limpieza de alumnos inactivos
│   │
│   ├── models/
│   │   ├── usuario.py                # Usuario, Profesor, Alumno, DetallesAlumno, Entrenamiento, cargo_de
│   │   └── evaluacion.py             # Categoria, Pregunta, Evaluacion, RespuestaEvaluacion
│   │
│   ├── services/
│   │   ├── dtos.py                   # Data Transfer Objects
│   │   ├── usuario_service.py        # CRUD multi-sesión de usuarios, profesores y alumnos
│   │   └── evaluacion_service.py     # CRUD y lógica de evaluaciones
│   │
│   └── ui/
│       ├── windows/
│       │   ├── login_window.py       # Pantalla de inicio de sesión
│       │   ├── main_window.py        # Ventana principal
│       │   ├── alumnos_page.py       # Lista de alumnos
│       │   └── alumno_detail.py      # Detalle del alumno
│       │
│       └── dialogs/
│           ├── crear_profesor_dialog.py
│           └── crear_alumno_dialog.py
│
├── migrations/
│   ├── env.py                        # Configuración de Alembic
│   └── versions/                     # Migraciones generadas
│
├── scripts/
│   ├── seed.py                       # Datos iniciales (categorías y preguntas con UUIDs fijos)
│   ├── sync.py                       # Sincronización remoto → local con detección de esquema
│   └── updater.py                    # Auto-actualización desde GitHub + migraciones Alembic
│
└── tests/
    ├── test_usuario_service.py
    └── test_evaluacion_service.py
```

---

## Base de datos

### Modelo de datos

- **Herencia joined-table:** `Usuario → Profesor / Alumno`
- **Medidas corporales:** `DetallesAlumno`
- **Evaluaciones:** `Evaluacion`, `RespuestaEvaluacion`, `Categoria`, `Pregunta`
- **Asignación profesor-alumno:** `cargo_de` (many-to-many)
- **Días de entrenamiento:** `Entrenamiento` (dia + horario por día)
- **PKs:** UUID generado en Python con `uuid.uuid4()` y `Uuid(as_uuid=True)` para compatibilidad SQLite + PostgreSQL — garantiza el mismo ID en ambas bases sin colisiones
- **Auditoría:** `updated_at` en `Usuario` y `created_at` en `Evaluacion` — permite ordenar por última modificación y determinar correctamente la última evaluación cuando hay varias el mismo día

### Escritura dual (local + remota)

Todos los servicios reciben una lista de sesiones via `get_sessions()` desde `database.py`.
Cada operación de escritura se replica en todas las sesiones disponibles:

```python
# Obtener sesiones (local siempre, remota si está configurada)
from app.database import get_sessions
service = UsuarioService(get_sessions())

# Las lecturas usan sessions[0] (local)
# Las escrituras iteran todas las sesiones
```

Esto garantiza que cualquier dato creado en la app queda en ambas bases simultáneamente.

### Sincronización remoto → local

La base remota (Neon) es la fuente de verdad. Al iniciar la app:

1. `updater.py` verifica commits nuevos en GitHub y reinicia si aplica.
2. `alembic upgrade head` corre automáticamente (con o sin actualización de código).
3. `sync.py` sincroniza datos de remoto → local, tabla por tabla:
   - Detecta y agrega columnas nuevas automáticamente (`ALTER TABLE`)
   - Inserta registros que están en remota y no en local
   - Actualiza registros que difieren
   - Elimina registros locales que ya no existen en remota

```bash
# Generar migración al modificar un modelo
alembic revision --autogenerate -m "descripcion"
alembic upgrade head
```

### Datos iniciales (seed)

Las categorías y preguntas de evaluación usan **UUIDs fijos hardcodeados** en `scripts/seed.py`.
Esto garantiza que los IDs sean idénticos en remota y local sin importar el orden de inserción.
Solo se ejecuta una vez contra la DB remota; el sync las baja automáticamente a local.

### Estado global (AppState)

`app/state.py` actúa como store en memoria. Las vistas leen del state y se suscriben a sus señales para actualizarse automáticamente cuando hay cambios.

- `state.cargar_alumnos()` → recarga desde DB local y emite `alumnos_changed`
- `state.cargar_profesores()` → recarga desde DB local y emite `profesores_changed`
- Las vistas **nunca escriben** al state directamente — siempre pasan por el service

---

## Auto-actualización

Al arrancar `python main.py` se ejecuta automáticamente:

1. **Verificar GitHub** — compara commit local vs remoto
2. **Si hay update:** `git pull` → `alembic upgrade head` → reinicia la app
3. **Si está al día:** `alembic upgrade head` (por migraciones pendientes)
4. **Sync de datos** — remota → local
5. **Scheduler** — job de limpieza de alumnos inactivos cada 24hs (corre contra DB remota)

Para desplegar un cambio desde casa basta con hacer `git push`. La próxima vez que abran la app en el gimnasio se actualiza sola.

---

## UI

### Flujo de navegación

1. **Login** — selección de perfil estilo Netflix. Si no hay profesores, muestra botón para crear uno.
2. **Main Window** — navbar con menú Crear (izquierda) y botón cerrar sesión (derecha).
3. **Tabs fijos** — Alumnos y Evaluaciones.
4. **Tabs dinámicos** — al clickear un alumno se abre una pestaña con su detalle, con botón X para cerrar.

### Vista detalle del alumno

- **Pestaña General:** datos personales, días de entrenamiento con horario, medidas corporales más recientes, botones de acción.
- **Pestaña Evaluaciones:** en construcción.
- Botón activar/desactivar con confirmación. Al desactivar, cierra la pestaña y redirige a Alumnos.

### Menú Crear

- Nuevo alumno (nombre, apellido, teléfono, tel. emergencia, usuario, fecha de nacimiento, días de entrenamiento con horario individual por día)
- Nuevo profesor (solo visible para jefes)
- Nueva evaluación (en construcción)

---

## Tests

```bash
pytest tests/ -v
```

Todos los tests usan SQLite en memoria y sesiones como lista (`[session]`) — no requieren conexión a Neon.

---

## Build ejecutable

```bash
python scripts/build.py
# Genera dist/GymManager.exe
```

---

## Módulos

- [x] Modelos: Usuario, Profesor, Alumno, DetallesAlumno, Entrenamiento, Evaluacion
- [x] PKs con UUID generado en Python (compatible SQLite + PostgreSQL, sin colisiones entre DBs)
- [x] Campo `updated_at` en Usuario para ordenar por última modificación
- [x] Campo `created_at` en Evaluacion para ordenar correctamente evaluaciones del mismo día
- [x] Servicios multi-sesión: escritura dual automática en local y remota
- [x] `get_sessions()` en database.py — abstrae la cantidad de DBs activas
- [x] Sync remoto → local (unidireccional, con detección y aplicación de columnas nuevas)
- [x] Auto-updater desde GitHub con `alembic upgrade head` integrado
- [x] Datos de seed con UUIDs fijos (categorías y preguntas reproducibles)
- [x] Store global en memoria (AppState con señales PyQt)
- [x] Job de limpieza de alumnos inactivos (APScheduler, corre contra DB remota)
- [x] Login estilo Netflix con creación de profesor si no hay ninguno
- [x] Ventana principal con navbar, menú Crear y cerrar sesión
- [x] Lista de alumnos con búsqueda, filtro por estado y filtro por día
- [x] Tabs dinámicos por alumno con botón cerrar
- [x] Vista detalle del alumno (datos personales + medidas corporales recientes)
- [x] Activar/desactivar alumno con confirmación
- [x] Crear alumno con días de entrenamiento y horario por día
- [x] Crear profesor (solo jefes)
- [ ] Editar alumno
- [ ] Agregar medidas corporales
- [ ] Gestión de evaluaciones
- [ ] Rutinas (diferido)