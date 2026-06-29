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

# 4. Aplicar migraciones (crea tablas en local y remoto)
alembic upgrade head

# 5. Cargar datos iniciales (categorías y preguntas de evaluación)
python scripts/seed.py

# 6. Correr la app
python main.py
```

---

## Estructura del proyecto
gym-manager/
├── main.py                          # Entry point
├── alembic.ini                      # Config de migraciones
├── requirements.txt
├── .env                             # Variables de entorno (no commitear)
├── app/
│  ├── database.py                  # Engines SQLite + PostgreSQL, Base ORM, Sessions
│  ├── state.py                     # Store global en memoria (AppState singleton + señales PyQt)
│  ├── models/
│  │   ├── usuario.py               # Usuario, Profesor, Alumno, DetallesAlumno, Entrenamiento, cargo_de
│  │   └── evaluacion.py            # Categoria, Pregunta, Evaluacion, RespuestaEvaluacion
│  ├── services/
│  │   ├── dtos.py                  # DataClasses (DTOs) para inputs de servicios
│  │   ├── usuario_service.py       # CRUD de usuarios, profesores, alumnos (acepta lista de sesiones)
│  │   └── evaluacion_service.py    # CRUD y lógica de evaluaciones
│  └── ui/
│      ├── windows/
│      │   ├── login_window.py      # Pantalla de selección de perfil (estilo Netflix)
│      │   ├── main_window.py       # Ventana principal con navbar, menú Crear y tabs de alumnos
│      │   ├── alumnos_page.py      # Lista de alumnos con búsqueda y filtros
│      │   └── alumno_detail.py     # Vista detalle del alumno con pestañas (General / Evaluaciones)
│      └── dialogs/
│          ├── crear_profesor_dialog.py
│          └── crear_alumno_dialog.py
├── migrations/
│  ├── env.py                       # Config Alembic — corre contra local y remoto simultáneamente
│  └── versions/                    # Archivos de migración generados
├── scripts/
│  ├── seed.py                      # Carga categorías y preguntas iniciales
│  ├── sync.py                      # Sincronización unidireccional remoto → local
│  └── updater.py                   # Auto-actualización desde GitHub via git pull
└── tests/
    ├── test_usuario_service.py
    └── test_evaluacion_service.py
---

## Base de datos

### Modelo de datos

- **Herencia joined-table:** `Usuario → Profesor / Alumno`
- **Medidas corporales:** `DetallesAlumno`
- **Evaluaciones:** `Evaluacion`, `RespuestaEvaluacion`, `Categoria`, `Pregunta`
- **Asignación profesor-alumno:** `cargo_de` (many-to-many)
- **Días de entrenamiento:** `Entrenamiento` (dia + horario por día)
- **PKs:** UUID generado en Python con `uuid.uuid4()` y `Uuid(as_uuid=True)` para compatibilidad SQLite + PostgreSQL
- **Auditoría:** `updated_at` en `Usuario` — permite ordenar alumnos por última modificación

### Sincronización local ↔ remoto

La base remota (Neon) es la fuente de verdad. Al iniciar la app:

1. `updater.py` verifica si hay commits nuevos en GitHub y reinicia si aplica.
2. `sync.py` sincroniza los datos de remoto → local (unidireccional, tabla por tabla).
3. Las migraciones Alembic corren contra **ambas bases simultáneamente**.

```bash
# Generar migración al modificar un modelo
alembic revision --autogenerate -m "descripcion"
alembic upgrade head
```

### Estado global (AppState)

`app/state.py` actúa como store en memoria. Las vistas leen del state y se suscriben a sus señales para actualizarse automáticamente cuando hay cambios.

- `state.cargar_alumnos()` → recarga desde DB local y emite `alumnos_changed`
- `state.cargar_profesores()` → recarga desde DB local y emite `profesores_changed`
- Las vistas **nunca escriben** al state directamente — siempre pasan por el service

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
- [x] Campo `updated_at` en Usuario para ordenar por última modificación
- [x] Servicios: UsuarioService (multi-sesión), EvaluacionService
- [x] Sync remoto → local (unidireccional)
- [x] Auto-updater desde GitHub
- [x] Store global en memoria (AppState con señales PyQt)
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
