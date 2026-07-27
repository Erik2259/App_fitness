# Desplegar en Railway (para verlo desde el iPhone)

Railway construye el backend desde `backend/Dockerfile` y le da una **URL HTTPS
pública** que puedes abrir en Safari del iPhone (`https://<tu-dominio>/docs`).

> Railway **no usa `docker-compose`**: se crean dos servicios independientes (la
> base de datos PostgreSQL y el backend) dentro de un mismo proyecto.

El código ya está preparado para Railway:
- la URL `postgresql://` que entrega Railway se normaliza sola al driver `asyncpg`;
- el backend escucha en el puerto `$PORT` que asigna Railway;
- las tablas se crean solas al arrancar (`auto_create_tables=True`).

---

## Paso a paso

### 1. Crear el proyecto desde GitHub
1. Entra en [railway.app](https://railway.app) e inicia sesión con GitHub.
2. **New Project → Deploy from GitHub repo → `Erik2259/App_fitness`**.
3. Railway creará un servicio a partir del repo. Aún no funcionará: falta decirle
   dónde está el Dockerfile y añadir la base de datos.

### 2. Apuntar el servicio al subdirectorio `backend`
En el servicio del backend → **Settings → Source**:
- **Root Directory** = `backend`

Así Railway detecta `backend/Dockerfile` y lo construye con el contexto correcto.

### 3. Añadir PostgreSQL
En el proyecto → **New → Database → Add PostgreSQL**.
Railway crea un servicio llamado `Postgres` con su propia `DATABASE_URL`.

### 4. Variables de entorno del backend
En el servicio del backend → **Variables**, añade:

| Variable | Valor | Nota |
|----------|-------|------|
| `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` | Referencia al servicio de BD (red privada). Si tu BD no se llama `Postgres`, ajusta el nombre. |
| `SECRET_KEY` | *(un secreto aleatorio)* | Genera uno: `python -c "import secrets; print(secrets.token_urlsafe(32))"` |
| `ENVIRONMENT` | `production` | Apaga el log de SQL. |
| `ANTHROPIC_API_KEY` | *(opcional)* | Sin ella, el coach responde en modo *dry-run*. Ponla para recibir recomendaciones reales de Claude. |
| `LLM_MODEL` | `claude-sonnet-4-5` | Opcional. |

### 5. Generar el dominio público
En el servicio del backend → **Settings → Networking → Generate Domain**.
Cuando pregunte **"Enter the port your app is listening on"**, deja el valor
sugerido **`8080`** y pulsa *Generate Domain*. Railway inyecta la variable `PORT`
con ese número y el contenedor (`uvicorn --port ${PORT:-8000}`) escucha ahí, así que
coinciden. Obtendrás un dominio como `app-fitness-production.up.railway.app`.

> Si tras el deploy ves **"Application failed to respond" (502)**, añade en
> **Variables** un `PORT=8080` explícito para forzar el puerto y redeploya.

*(Opcional)* En **Settings → Deploy → Healthcheck Path** pon `/health` para que
Railway valide cada despliegue.

### 6. Abrir desde el iPhone
En Safari:
- **Dashboard (frontend):** `https://<tu-dominio>/` → crea cuenta, inicia sesión y ve tu carga, recuperación y la recomendación del coach.
- **Salud:** `https://<tu-dominio>/health` → `{"status":"ok","environment":"production"}`
- **Docs de la API:** `https://<tu-dominio>/docs` (consola para probar endpoints a mano).

### 7. Meter tus datos de HealthKit (sin Mac)
1. Instala **"Health Auto Export — JSON+CSV"** desde la App Store.
2. Crea una automatización **REST API** hacia
   `https://<tu-dominio>/api/v1/ingesta/health-auto-export`.
3. Header: `Authorization: Bearer <token>` (obtén el token en el dashboard tras
   iniciar sesión, o en `/docs` → `/auth/login`).
4. Selecciona workouts, HRV, RHR y sueño, y la frecuencia de envío.

Al recibir el JSON, el backend crea los entrenamientos (con su TRIMP) y actualiza
las métricas diarias. Luego, en el dashboard, pulsa **Recalcular estado (K-Means)** y
**Pedir recomendación**.

---

## Notas

- **Primer arranque:** si el backend arranca antes de que Postgres esté listo, el
  contenedor puede reiniciarse una o dos veces y luego estabilizarse. Es normal.
- **Redeploys:** cada `git push` a `main` dispara un nuevo despliegue automático.
- **Migraciones:** para este despliegue las tablas se crean solas. Cuando quieras un
  esquema versionado, pon `AUTO_CREATE_TABLES=false` y usa Alembic
  (`alembic upgrade head`) en un comando de release.
- **Coste:** Railway ofrece un crédito de prueba y luego cobra por uso. Una API
  pequeña + Postgres suele mantenerse dentro de márgenes bajos, pero revísalo.
- **CORS:** por defecto se permiten todos los orígenes (`CORS_ORIGINS=["*"]`). Cuando
  publiques el frontend, restríngelo a tu dominio.
