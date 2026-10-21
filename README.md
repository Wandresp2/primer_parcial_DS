# Óptica y Fotónica — MySQL + Streamlit

| | |
|--|--|
| Repo | https://github.com/Wandresp2/primer_parcial_DS.git |
| UI | http://localhost:8501 |
| Imagen | `andresperez3/optica-fotonica:latest` |
| MySQL | `root` / `root` — DB `optica_y_fotonica` — puerto `3306` |

Requisito: Docker + Git.

---

## 1. Clonar e ir al proyecto

```bash
git clone https://github.com/Wandresp2/primer_parcial_DS.git
cd primer_parcial_DS
```

---

## 2. Levantar el sistema

```bash
docker compose pull
docker compose up -d --no-build
```

- `pull` — baja las imágenes de Hub (`mysql:8.4` y la app).
- `up -d --no-build` — crea e inicia los contenedores.

Abrir: **http://localhost:8501**

---

## 3. Si falla por puerto ocupado (3306 o 8501)

**Menos agresivo — detener** los contenedores que usan esos puertos:

```bash
docker stop $(docker ps -q --filter publish=3306)
docker stop $(docker ps -q --filter publish=8501)
```

**Más agresivo — eliminar** esos contenedores:

```bash
docker rm -f $(docker ps -aq --filter publish=3306)
docker rm -f $(docker ps -aq --filter publish=8501)
```

Luego vuelve a levantar:

```bash
docker compose pull
docker compose up -d --no-build
```

Abrir: **http://localhost:8501**

---

## 4. Detener el proyecto

```bash
docker compose down
```

Apaga los contenedores y conserva los datos de MySQL.

```bash
docker compose down -v
```

Apaga y **borra** el volumen MySQL (`init.sql` se vuelve a cargar al subir de nuevo).

---

## 5. Volver a correr

Desde la carpeta del repo (`cd primer_parcial_DS` si hace falta):

```bash
docker compose pull
docker compose up -d --no-build
```

Si el puerto vuelve a estar ocupado, usa el paso 3 y después estos mismos dos comandos.

---

## Windows (PowerShell)

Los mismos comandos; si `$(...)` falla al liberar puertos:

```powershell
docker stop $(docker ps -q --filter publish=3306)
docker stop $(docker ps -q --filter publish=8501)
docker rm -f $(docker ps -aq --filter publish=3306)
docker rm -f $(docker ps -aq --filter publish=8501)
```

---

Docs técnicos: [docs/](docs/) · Playbook Docker: [docs/guia_docker_hub_sistema_portable.md](docs/guia_docker_hub_sistema_portable.md)

Autor: Perez Criollo Andres David
