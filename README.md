# Óptica y Fotónica — MySQL + Streamlit (NIST ASD)

Datos atómicos (H–Ne) del [NIST Atomic Spectra Database](https://physics.nist.gov/PhysRefData/ASD/) en MySQL 8.4 + UI Streamlit.

**Entrega (opción A del taller):** una imagen tuya en Docker Hub + `init.sql` en el repo + `docker compose`.

**Un solo comando** (`./lab-arranque.sh` o `.\lab-arranque.ps1`) reproduce el sistema completo.

| Pieza | Valor |
|-------|--------|
| Imagen UI (Hub) | `andresperez3/optica-fotonica:latest` |
| MySQL | `mysql:8.4` (oficial) + mount de `./init.sql` |
| UI | http://localhost:8501 |

---

## Para quien ejecuta el proyecto (profe / desde cero)

### Requisitos

- Docker Engine + Compose (en Windows: Docker Desktop con integración **WSL2**)
- Bash (Linux nativo o **WSL**) o PowerShell
- Puertos libres **3306** (MySQL) y **8501** (Streamlit)
- Internet (imágenes de Docker Hub; pip solo si reconstruyes la imagen en local)
- Clonar este repo (hacen falta `docker-compose.yml` + `init.sql`)

### Opción recomendada (libera puertos y usa Hub)

**Linux / WSL:**

```bash
chmod +x lab-arranque.sh
./lab-arranque.sh
```

**Windows (PowerShell), en la raíz del repo:**

```powershell
.\lab-arranque.ps1
```

Ese script:

1. Elimina contenedores que ocupen los puertos **3306** y **8501**
2. `docker compose down -v` (solo este proyecto)
3. `docker compose pull` (baja `andresperez3/optica-fotonica:latest` + `mysql:8.4`)
4. `docker compose up -d --no-build` (no reconstruye; usa Hub, como Lab 10 del PDF)

Luego abre **http://localhost:8501**.

### Opción manual (como el PDF)

```bash
docker compose down -v
docker compose pull
docker compose up -d --no-build
```

Si aún no existe la imagen en Hub y tienes el código:

```bash
docker compose up -d --build
```

---

## Para ti (autor): actualizar y subir la imagen a Docker Hub

Haz esto cuando cambies `app/` o `requirements.txt`.

### Paso a paso

1. Abre Docker Desktop (o el daemon) y ten red.
2. En la raíz del repo, reconstruye la imagen con el nombre de Hub:
   ```bash
   docker compose build streamlit
   ```
   Eso deja lista: `andresperez3/optica-fotonica:latest`
3. Inicia sesión en Docker Hub:
   ```bash
   docker login -u andresperez3
   ```
   (Si tienes 2FA, usa un **Access Token** como contraseña.)
4. Sube la imagen:
   ```bash
   docker push andresperez3/optica-fotonica:latest
   ```
5. Comprueba en https://hub.docker.com/r/andresperez3/optica-fotonica
6. Verifica “como otra persona” (Lab 10 del PDF):
   ```bash
   docker compose down -v
   docker rmi andresperez3/optica-fotonica:latest
   docker compose pull
   docker compose up -d --no-build
   ```
   Debe bajar la imagen de Hub y abrir http://localhost:8501 sin usar `build`.

> En el PDF, el paso equivalente a `--no-build` es **comentar la línea `build:`** en el compose y hacer `docker compose up -d`. Aquí `--no-build` hace lo mismo sin editar el YAML.

---

## Compose: qué es el servicio `streamlit`

Dos contenedores en la red `optica_net`:

| Servicio | Rol |
|----------|-----|
| `mysql` | Base de datos; datos desde `init.sql` |
| `streamlit` | Web en el puerto 8501 |

- `image:` → nombre en Hub  
- `build:` → cómo fabricarla en local (Lab 8 del PDF)  
- `MYSQL_HOST=mysql` → nombre del servicio en la red (no `localhost`)

```text
Navegador → localhost:8501 → streamlit → red → mysql:3306
```

---

## Credenciales (laboratorio)

| Campo | Valor |
|-------|--------|
| MySQL host (entre contenedores) | `mysql` |
| MySQL host (desde tu PC) | `localhost:3306` |
| Usuario / password | `root` / `root` |
| Base | `optica_y_fotonica` |

---

## Comandos útiles

```bash
docker compose ps
docker compose logs -f streamlit
docker compose down          # apaga; conserva volumen
docker compose down -v       # apaga; borra datos (init.sql vuelve a correr)
```

## Estructura

```text
docker-compose.yml      # mysql + streamlit (image Hub + build)
Dockerfile
requirements.txt
init.sql                # schema + datos (mount en MySQL)
lab-arranque.sh         # Linux: libera puertos + pull + up
lab-arranque.ps1        # Windows: igual
app/
  streamlit_app.py      UI (7 secciones + filtros)
  db.py                 Conexión MySQL
docs/                   # historial del parcial (no va en la imagen)
README.md
```

## Documentación técnica

| Doc | Contenido |
|-----|-----------|
| [docs/02_…](docs/02_exploracion_caracterizacion_datos.md) | Diagnóstico (historial) |
| [docs/03_…](docs/03_limpieza_datos.md) | Limpieza L1–L14 (historial) |
| [docs/04_…](docs/04_pipeline_etl_mysql.md) | ETL (historial) |
| [docs/05_…](docs/05_consultas_analisis_cientifico.md) | UI / consultas |

## Autor

Perez Criollo Andres David  
Docker Hub: `andresperez3/optica-fotonica`
