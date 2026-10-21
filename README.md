# Óptica y Fotónica — MySQL + Streamlit (NIST ASD)

Datos atómicos (H–Ne) del [NIST Atomic Spectra Database](https://physics.nist.gov/PhysRefData/ASD/) en MySQL 8.4 + interfaz Streamlit.

| Pieza | Valor |
|-------|--------|
| Repositorio | https://github.com/Wandresp2/primer_parcial_DS.git |
| Imagen UI (Docker Hub) | `andresperez3/optica-fotonica:latest` |
| MySQL | `mysql:8.4` + `./init.sql` |
| UI | http://localhost:8501 |
| Puertos | **3306** (MySQL), **8501** (Streamlit) |
| Credenciales lab | usuario `root` / password `root` / DB `optica_y_fotonica` |

---

## Requisitos

- Docker Engine + Compose (Windows: Docker Desktop)
- Git
- Internet (primera vez: pull de imágenes)

---

## Arranque desde cero (en orden)

Ejecuta los bloques **en secuencia**, desde una terminal. Primero se documenta **Linux** (principal); al final hay variante **Windows**.

### Linux (principal)

#### 1) Clonar el repositorio

```bash
git clone https://github.com/Wandresp2/primer_parcial_DS.git
cd primer_parcial_DS
```

#### 2) Si algún puerto está ocupado (3306 o 8501)

Si Docker o el `up` indica que el puerto está en uso, **detén** o **elimina** los contenedores que lo publican y luego sigue con el paso 3.

Ver qué contenedores usan esos puertos:

```bash
docker ps --filter publish=3306
docker ps --filter publish=8501
```

**Opción suave — solo detener** (los contenedores quedan parados, no se borran):

```bash
docker stop $(docker ps -q --filter publish=3306)
docker stop $(docker ps -q --filter publish=8501)
```

**Opción fuerte — eliminar** esos contenedores:

```bash
docker rm -f $(docker ps -aq --filter publish=3306)
docker rm -f $(docker ps -aq --filter publish=8501)
```

Si existen los nombres de este proyecto y estorban:

```bash
docker rm -f mysql_container streamlit_optica
```

> Si el puerto lo ocupa un programa **fuera** de Docker (MySQL instalado en el sistema), hay que pararlo a mano o cambiar los puertos en `docker-compose.yml`.

#### 3) Traer imágenes y levantar contenedores

```bash
docker compose down -v
docker compose pull
docker compose up -d --no-build
```

Qué hace cada línea:

1. `down -v` — apaga este proyecto y borra su volumen (así `init.sql` carga datos limpios).
2. `pull` — descarga `mysql:8.4` y `andresperez3/optica-fotonica:latest`.
3. `up -d --no-build` — crea/inicia los contenedores usando las imágenes de Hub (sin rebuild local).

#### 4) Abrir la plataforma

En el navegador: **http://localhost:8501**

Comprobar estado (opcional):

```bash
docker compose ps
```

---

### Windows (PowerShell) — misma secuencia

```powershell
git clone https://github.com/Wandresp2/primer_parcial_DS.git
cd primer_parcial_DS
```

Si el puerto está ocupado — **detener**:

```powershell
docker stop $(docker ps -q --filter publish=3306)
docker stop $(docker ps -q --filter publish=8501)
```

Si el puerto está ocupado — **eliminar**:

```powershell
docker rm -f $(docker ps -aq --filter publish=3306)
docker rm -f $(docker ps -aq --filter publish=8501)
docker rm -f mysql_container streamlit_optica
```

Luego:

```powershell
docker compose down -v
docker compose pull
docker compose up -d --no-build
```

Abrir: **http://localhost:8501**

---

## Si el `pull` falla (imagen aún no en Hub)

Con el código del repo en la carpeta del proyecto:

```bash
docker compose up -d --build
```

---

## Apagar, borrar o volver a correr

Ejecutar desde la raíz del repo (`primer_parcial_DS`).

| Objetivo | Comandos (Linux; en Windows igual con PowerShell) |
|----------|-----------------------------------------------------|
| Ver estado | `docker compose ps` |
| Ver logs Streamlit | `docker compose logs -f streamlit` |
| Apagar (conserva datos MySQL) | `docker compose down` |
| Apagar y borrar datos (reaplica `init.sql` al subir) | `docker compose down -v` |
| Volver a correr desde cero | Ver bloque de abajo |

**Volver a correr desde cero (en orden):**

```bash
cd primer_parcial_DS
docker compose down -v
docker compose pull
docker compose up -d --no-build
```

Si otra vez hay conflicto de puertos, repite antes los comandos de **detener** o **eliminar** del apartado de puertos ocupados.

---

## Credenciales

| Campo | Valor |
|-------|--------|
| Streamlit | http://localhost:8501 |
| MySQL (desde el host) | `localhost:3306` |
| Host MySQL (entre contenedores) | `mysql` |
| Usuario / password | `root` / `root` |
| Base de datos | `optica_y_fotonica` |

---

## Autor: actualizar imagen en Docker Hub

```bash
cd primer_parcial_DS
docker login -u andresperez3
docker compose build streamlit
docker push andresperez3/optica-fotonica:latest
```

Verificar como otra persona:

```bash
docker compose down -v
docker rmi andresperez3/optica-fotonica:latest
docker compose pull
docker compose up -d --no-build
```

---

## Estructura del repositorio

```text
docker-compose.yml      # mysql + streamlit
Dockerfile              # imagen de la app
requirements.txt
init.sql                # schema + datos (mount en MySQL)
app/
docs/                   # documentación (no va en la imagen)
README.md
```

## Más documentación

| Doc | Contenido |
|-----|-----------|
| [docs/guia_docker_hub_sistema_portable.md](docs/guia_docker_hub_sistema_portable.md) | Playbook para repetir este patrón en otro proyecto |
| [docs/02_…](docs/02_exploracion_caracterizacion_datos.md) | Diagnóstico (historial) |
| [docs/03_…](docs/03_limpieza_datos.md) | Limpieza (historial) |
| [docs/04_…](docs/04_pipeline_etl_mysql.md) | ETL (historial) |
| [docs/05_…](docs/05_consultas_analisis_cientifico.md) | UI / consultas |

## Autor

Perez Criollo Andres David  
Docker Hub: `andresperez3/optica-fotonica`
