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
│       ├── theme.py                  # Sistema de temas (modo oscuro / modo claro) con singleton
│       ├── windows/
│       │   ├── login_window.py       # Pantalla de inicio de sesión estilo Netflix
│       │   ├── main_window.py        # Ventana principal con navbar, tabs y menú Crear
│       │   ├── alumnos_page.py       # Lista de alumnos con búsqueda y filtros
│       │   └── alumno_detail.py      # Detalle del alumno con pestañas y submenús de acción
│       │
│       └── dialogs/
│           ├── crear_profesor_dialog.py
│           ├── crear_alumno_dialog.py
│           └── agregar_detalles_dialog.py
│
├── migrations/
│   ├── env.py                        # Configuración de Alembic (corre contra local y remoto)
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
- **Días de entrenamiento:** `Entrenamiento` (dia + horario individual por día)
- **PKs:** UUID generado en Python con `uuid.uuid4()` y `Uuid(as_uuid=True)` — mismo ID en ambas bases sin colisiones
- **Auditoría:** `updated_at` en `Usuario` (orden por última modificación), `created_at` en `Evaluacion`

### Estrategia de escritura

La app opera principalmente sobre la **base local (SQLite)**. La base remota (Neon) es el respaldo y fuente de verdad al inicio.

- **Lecturas** → siempre desde local
- **Escrituras** → solo local (Neon se actualiza al próximo sync o al iniciar la app)
- **Al iniciar** → sync remoto → local + migraciones automáticas

```python
# Los servicios reciben sesiones via get_sessions()
from app.database import LocalSession
service = UsuarioService([LocalSession()])
```

### Sincronización remoto → local

Al iniciar la app:

1. `updater.py` verifica commits nuevos en GitHub y reinicia si aplica.
2. `alembic upgrade head` corre automáticamente.
3. `sync.py` sincroniza datos de remoto → local, tabla por tabla.

```bash
# Generar migración al modificar un modelo
alembic revision --autogenerate -m "descripcion"
alembic upgrade head
```

### Estado global (AppState)

`app/state.py` actúa como store en memoria. Las vistas leen del state y se suscriben a sus señales para actualizarse automáticamente.

- `state.cargar_alumnos()` → recarga desde DB local y emite `alumnos_changed`
- `state.cargar_profesores()` → recarga desde DB local y emite `profesores_changed`
- Las vistas **nunca escriben** al state — siempre pasan por el service

---

## Temas (modo oscuro / modo claro)

`app/ui/theme.py` expone un singleton `theme` con dos paletas: `DARK` y `LIGHT` (blanco y negro).

```python
from app.ui.theme import theme

# Usar un color
color = theme['primario']

# Cambiar tema
theme.toggle()

# Suscribirse a cambios
theme.theme_changed.connect(mi_funcion)
```

El tema se puede togglear desde la navbar con un botón 🌙/☀️.

---

## Auto-actualización

Al arrancar `python main.py` se ejecuta automáticamente:

1. Verificar GitHub — compara commit local vs remoto
2. Si hay update: `git pull` → `alembic upgrade head` → reinicia la app
3. Si está al día: `alembic upgrade head` (por migraciones pendientes)
4. Sync de datos remoto → local
5. Scheduler — job de limpieza de alumnos inactivos cada 24hs

Para desplegar un cambio desde casa basta con hacer `git push`. La próxima vez que abran la app en el gimnasio se actualiza sola.

---

## UI

### Flujo de navegación

1. **Login** — selección de perfil estilo Netflix. Si no hay profesores, muestra botón para crear uno.
2. **Main Window** — navbar con menú Crear (izquierda) y botón cerrar sesión (derecha).
3. **Tabs fijos** — Alumnos y Evaluaciones.
4. **Tabs dinámicos** — al clickear un alumno se abre una pestaña con su detalle y botón X para cerrar.

### Vista detalle del alumno

- **Pestaña General:** datos personales, días de entrenamiento con horario, medidas corporales más recientes.
- **Pestaña Evaluaciones:** en construcción.
- Botón activar/desactivar con confirmación. Al desactivar, cierra la pestaña y redirige a Alumnos.
- El header y el tab General se reconstruyen automáticamente cuando cambia el state.

### Submenús de acción

Cada botón de acción tiene un menú desplegable:

| Botón | Opciones |
|---|---|
| 🏋️ Rutina | Crear rutina · Ver última |
| 📋 Evaluación | Crear evaluación · Ver última |
| 📏 Datos corporales | Añadir · Ver historial (gráfico) |
| ✏️ Editar | Abre diálogo de edición |

### Menú Crear (navbar)

- Nuevo alumno — nombre, apellido, teléfono, tel. emergencia, fecha de nacimiento, días con horario individual, opción de cargar datos corporales al crear
- Nuevo profesor (solo visible para jefes)
- Nueva evaluación (en construcción)

---

## Tests

```bash
pytest tests/ -v
```

Todos los tests usan SQLite en memoria — no requieren conexión a Neon.

---

## Build ejecutable

```bash
python scripts/build.py
# Genera dist/GymManager.exe
```

---

## Módulos

- [x] Modelos: Usuario, Profesor, Alumno, DetallesAlumno, Entrenamiento, Evaluacion
- [x] PKs con UUID generado en Python (compatible SQLite + PostgreSQL)
- [x] Campo `updated_at` en Usuario y `created_at` en Evaluacion
- [x] Servicios operan principalmente sobre DB local
- [x] Sync remoto → local al iniciar (unidireccional)
- [x] Auto-updater desde GitHub con `alembic upgrade head` integrado
- [x] Datos de seed con UUIDs fijos (categorías y preguntas reproducibles)
- [x] Store global en memoria (AppState con señales PyQt)
- [x] Sistema de temas oscuro/claro (singleton `theme` en `app/ui/theme.py`)
- [x] Job de limpieza de alumnos inactivos (APScheduler)
- [x] Login estilo Netflix con creación de profesor si no hay ninguno
- [x] Ventana principal con navbar, menú Crear y cerrar sesión
- [x] Lista de alumnos con búsqueda, filtro por estado y filtro por día
- [x] Tabs dinámicos por alumno con botón cerrar
- [x] Vista detalle del alumno con reconstrucción automática al cambiar state
- [x] Activar/desactivar alumno con confirmación y redirección a Alumnos
- [x] Crear alumno con días de entrenamiento y horario por día + datos corporales opcionales
- [x] Crear profesor (solo jefes)
- [x] Agregar medidas corporales desde detalle del alumno
- [x] Submenús de acción: Rutina, Evaluación, Datos corporales, Editar
- [ ] Editar alumno (diálogo)
- [ ] Ver última rutina / evaluación
- [ ] Historial de medidas corporales con gráfico
- [ ] Gestión completa de evaluaciones
- [ ] Rutinas (diferido)