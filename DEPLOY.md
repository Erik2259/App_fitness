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

> **No** definas `PORT`: Railway lo inyecta automáticamente y el contenedor ya lo usa.

### 5. Generar el dominio público
En el servicio del backend → **Settings → Networking → Generate Domain**.
Obtendrás algo como `app-fitness-production.up.railway.app`.

*(Opcional)* En **Settings → Deploy → Healthcheck Path** pon `/health` para que
Railway valide cada despliegue.

### 6. Abrir desde el iPhone
En Safari:
- **Docs interactivas:** `https://<tu-dominio>/docs`
- **Salud:** `https://<tu-dominio>/health` → `{"status":"ok","environment":"production"}`

Desde `/docs` puedes registrar un usuario, hacer login (botón **Authorize**) y probar
todos los endpoints directamente desde el móvil.

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
