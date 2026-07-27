# AI Fitness & Performance Coach

Backend en FastAPI + PostgreSQL, containerizado con Docker, para un coach de alto
rendimiento orientado a atletas híbridos (running + fuerza/calistenia).

Filosofía del proyecto: **todo cálculo cuantitativo se hace en Python** (TRIMP,
tonelaje, clustering de recuperación). El LLM (Claude) solo **interpreta** métricas
ya calculadas y genera la recomendación; nunca estima ni inventa cifras.

## Fases implementadas

| Fase | Descripción | Dónde vive |
|------|-------------|------------|
| **1 · Infraestructura y datos** | Modelos SQLAlchemy, Docker, Alembic, config | `app/models`, `app/db`, `app/core` |
| **2 · Cálculo de carga** | TRIMP (Banister, FC de reserva) y tonelaje con Pandas | `app/services/carga.py` |
| **3 · Clustering de recuperación** | K-Means (scikit-learn) sobre el snapshot diario | `app/services/clustering.py` |
| **4 · Coach LLM** | Prompt dinámico + cliente Anthropic Claude | `app/services/prompt_builder.py`, `app/services/llm.py` |
| **+ API REST** | Auth JWT + endpoints para que Flutter envíe HealthKit | `app/api` |

## Estructura del proyecto

```
App_fitness/
├── docker-compose.yml
├── .env.example
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── pytest.ini
│   ├── migrations/                 # Migraciones de esquema (Alembic)
│   ├── tests/                      # Tests de las fases 2–4 (lógica pura)
│   └── app/
│       ├── main.py                 # Instancia de FastAPI + montaje del router
│       ├── core/
│       │   ├── config.py           # Settings (pydantic-settings)
│       │   └── security.py         # Hash de contraseñas (bcrypt) + JWT
│       ├── db/                     # Base declarativa + sesión async
│       ├── models/                 # Usuario, Entrenamiento, MetricaBiometrica
│       ├── schemas/                # Contratos Pydantic (entrada/salida)
│       ├── crud/                   # Acceso a datos async
│       ├── services/               # Fases 2, 3 y 4 (lógica de negocio)
│       └── api/
│           ├── deps.py             # Sesión de BD + usuario autenticado
│           └── v1/                 # auth, usuarios, entrenamientos, metricas, coach
```

## Cómo levantar el proyecto

```bash
cp .env.example .env          # ajusta credenciales y (opcional) ANTHROPIC_API_KEY
docker-compose up --build
```

- API disponible en `http://localhost:8000`
- Docs interactivas (Swagger) en `http://localhost:8000/docs`
- Endpoint de salud: `GET /health`
- Postgres expuesto en `localhost:5432` (útil para DBeaver/TablePlus)

En modo `development` (default), `main.py` crea las tablas automáticamente al
arrancar. Para producción, usa Alembic:

```bash
docker-compose exec backend alembic revision --autogenerate -m "esquema inicial"
docker-compose exec backend alembic upgrade head
```

## Desplegar en la nube

Para verlo desde el móvil (iPhone/Android) con una URL pública, sigue
[`DEPLOY.md`](DEPLOY.md) — guía paso a paso para **Railway** (PostgreSQL gestionado
+ backend desde el Dockerfile). El código ya normaliza la `DATABASE_URL` del
proveedor y escucha en el puerto `$PORT` que asigna la plataforma.

## API (v1)

Todos los endpoints de datos requieren un JWT (`Authorization: Bearer <token>`),
que se obtiene en `/auth/login`. El prefijo es `/api/v1`.

| Método | Ruta | Descripción |
|--------|------|-------------|
| `POST` | `/auth/register` | Alta de atleta (email único) |
| `POST` | `/auth/login` | Login (form `username`=email, `password`) → JWT |
| `GET`  | `/auth/me` · `/usuarios/me` | Perfil del atleta autenticado |
| `PATCH`| `/usuarios/me` | Actualiza perfil y datos fisiológicos base |
| `POST` | `/entrenamientos` | Registra sesión de HealthKit y **calcula su TRIMP** (Fase 2) |
| `GET`  | `/entrenamientos` | Lista sesiones (más recientes primero) |
| `GET`  | `/entrenamientos/{id}` | Detalle de una sesión |
| `POST` | `/metricas-biometricas` | Upsert del snapshot diario (uno por fecha) |
| `GET`  | `/metricas-biometricas` | Historial de snapshots |
| `POST` | `/metricas-biometricas/clasificar` | **Fase 3**: corre K-Means y persiste el clúster de cada día |
| `POST` | `/coach/recomendacion` | **Fase 4**: arma el contexto y pide la recomendación al LLM |

### Ejemplo de flujo

```bash
# 1) Registro
curl -X POST localhost:8000/api/v1/auth/register -H "Content-Type: application/json" \
  -d '{"email":"erik@example.com","password":"supersegura","nombre":"Erik","fc_maxima":190,"fc_reposo":48,"sexo":"masculino"}'

# 2) Login (OAuth2 password flow → token)
TOKEN=$(curl -s -X POST localhost:8000/api/v1/auth/login \
  -d "username=erik@example.com&password=supersegura" | python -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

# 3) Enviar un entrenamiento (el backend calcula el TRIMP)
curl -X POST localhost:8000/api/v1/entrenamientos -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"tipo":"running","fecha_inicio":"2026-07-27T07:00:00Z","duracion_segundos":3600,"fc_promedio":155,"distancia_m":10000,"cadencia_spm":178}'

# 4) Pedir la recomendación del coach
curl -X POST localhost:8000/api/v1/coach/recomendacion -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" -d '{"ventana_dias":7}'
```

## Diseño de los modelos

**Usuario** — perfil del atleta y sus datos fisiológicos base (FC máxima, FC de
reposo, FTP de running). Son la referencia contra la que el backend calcula el
TRIMP en la Fase 2.

**Entrenamiento** — una sesión individual desde HealthKit: esfuerzo
cardiovascular (`fc_promedio`, `trimp`), biomecánica de running (`cadencia_spm`,
`oscilacion_vertical_cm`, `tiempo_contacto_suelo_ms`, potencia), fuerza/calistenia
(`tonelaje_kg`, `series_totales`) y `datos_crudos` (JSON) con el payload original.

**MetricaBiometrica** — snapshot diario de recuperación (sueño por fases, HRV, FC
de reposo, deuda de sueño, carga metabólica) más `cluster_recuperacion`, que la
Fase 3 actualiza. Índice único por `(usuario_id, fecha)`.

Todos los IDs son UUID, pensando en que Flutter pueda generar IDs offline antes de
sincronizar.

## Detalle de las fases de cálculo

- **Fase 2 — TRIMP**: método de Banister ponderado por FC de reserva,
  `TRIMP = min · HRr · 0.64 · e^(k·HRr)`, con coeficiente `k` por sexo. Se calcula
  al crear el entrenamiento, a partir de la FC de la sesión y la FCmax/FCreposo del
  usuario.
- **Fase 3 — K-Means**: agrupa cada día en 3 clústers usando
  `deuda_sueno_min`, `carga_metabolica`, `hrv_ms`, `rhr_bpm` (estandarizados). Los
  centroides se ordenan por un "índice de fatiga" interpretable para asignarles las
  etiquetas `optimo` / `alerta_fatiga` / `sobreentrenamiento`.
- **Fase 4 — Coach LLM**: el prompt combina el estado de recuperación (Fase 3), la
  carga agregada (Fase 2) y la biomecánica de la última carrera. Si no hay
  `ANTHROPIC_API_KEY`, funciona en **dry-run** (devuelve el prompt sin llamar al
  modelo), útil para desarrollo y tests.

## Tests

Los tests cubren la lógica pura de las fases 2–4 (no requieren base de datos):

```bash
docker-compose exec backend pytest
# o en local, dentro de backend/ con las dependencias instaladas:
pytest
```
