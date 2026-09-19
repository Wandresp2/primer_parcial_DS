# JupyterLab + MySQL 8.4 con Docker Compose

Stack de dos contenedores en la red Docker `jupyter_mysql`. Desde un notebook se consulta MySQL usando el nombre del servicio (`mysql`), no `localhost`.

## Requisitos

- Docker Desktop encendido
- La red `jupyter_mysql` ya creada. Si no existe:

```bash
docker network create jupyter_mysql
```

## Arranque

1. Copia las variables de entorno (solo la primera vez):

```bash
cp .env.example .env
```

En Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

2. Levanta los servicios:

```bash
docker compose up -d
```

3. Abre JupyterLab en [http://localhost:8888](http://localhost:8888) con el token de `.env` (`JUPYTER_TOKEN`, por defecto `facil123`).

4. Comprueba el estado:

```bash
docker compose ps
```

Ambos contenedores deben aparecer en la red `jupyter_mysql`. Compose reutiliza las imagenes locales `mysql:8.4` y `quay.io/jupyter/scipy-notebook:latest` si ya las tienes; si no, las descarga.

## Conexion desde un notebook

Host: `mysql` (nombre del servicio en `docker-compose.yml`). Puerto: `3306`.

Hay un notebook de prueba en `notebooks/conexion_mysql.ipynb`. Ejemplo:

```python
%pip install mysql-connector-python

import mysql.connector

conn = mysql.connector.connect(
    host="mysql",
    port=3306,
    user="usuario",
    password="usuariopass",
    database="mi_db",
)

cursor = conn.cursor()
cursor.execute("SELECT VERSION();")
print(cursor.fetchone())
cursor.close()
conn.close()
```

Ajusta usuario, contrasena y base si cambiaste el `.env`.

## Persistencia

- Los datos de MySQL viven en el volumen nombrado `mysql_data`. Sobreviven a `docker compose down` y a recrear contenedores.
- Los notebooks se guardan en `./notebooks`.

Detener sin borrar la base:

```bash
docker compose down
```

Borrar tambien el volumen de MySQL (se pierde la informacion):

```bash
docker compose down -v
```

No uses `-v` si quieres conservar los datos.
