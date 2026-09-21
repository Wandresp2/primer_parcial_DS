# JupyterLab + MySQL 8.4 con Docker Compose

Stack de dos contenedores conectados por una red Docker que Compose crea automaticamente (`jupyter_mysql`, driver `bridge`). Desde un notebook se consulta MySQL usando el nombre del servicio (`mysql`), no `localhost`.

## Requisitos

- Docker Desktop encendido
- Los puertos **3306** (MySQL) y **8888** (JupyterLab) deben estar **libres** en tu maquina. Si ya hay otro MySQL, XAMPP, MariaDB, otro Jupyter u otro contenedor usando esos puertos, `docker compose up` fallara. Libera esos puertos o cambia el mapeo en `docker-compose.yml` (por ejemplo `"3307:3306"` o `"8889:8888"`).

No necesitas crear la red a mano: Compose la crea al levantar el stack.

## Arranque

1. Copia las variables de entorno (solo la primera vez):

```bash
cp .env.example .env
```

En Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

2. Levanta los servicios (crea red, volumen y contenedores):

```bash
docker compose up -d
```

3. Abre JupyterLab en [http://localhost:8888](http://localhost:8888) con el token de `.env` (`JUPYTER_TOKEN`, por defecto `facil123`).

4. Crea la base de datos del proyecto y sus tablas ejecutando `sql/schema.sql` en DBeaver (conectado al servidor MySQL, sin necesidad de una base previa). El script hace `CREATE DATABASE optica_y_fotonica` y luego las 9 tablas vacias. Equivalente por terminal:

```bash
docker exec -i mysql_container mysql -uroot -proot < sql/schema.sql
```

En PowerShell, si la redireccion `<` falla:

```powershell
Get-Content sql/schema.sql -Raw | docker exec -i mysql_container mysql -uroot -proot
```

5. Comprueba el estado:

```bash
docker compose ps
```

Compose reutiliza las imagenes locales `mysql:8.4` y `quay.io/jupyter/scipy-notebook:latest` si ya las tienes; si no, las descarga.

## Credenciales por defecto (`.env.example`)

| Variable | Valor |
|---|---|
| `MYSQL_ROOT_PASSWORD` | `root` |
| `MYSQL_DATABASE` | `optica_y_fotonica` |
| `JUPYTER_TOKEN` | `facil123` |

Nota: en la imagen oficial de MySQL, `MYSQL_USER` no puede ser `root`. Para root usa solo `MYSQL_ROOT_PASSWORD`.

La base de trabajo del proyecto es **`optica_y_fotonica`**. La crea `sql/schema.sql`; el pipeline ETL y los notebooks se conectan a esa base, no a `db_prueba`.

## Conexion desde un notebook

Host: `mysql` (nombre del servicio en `docker-compose.yml`). Puerto: `3306`.

Hay un notebook de prueba en `notebooks/conexion_mysql.ipynb`. Las consultas SQL y la respuesta a la pregunta cientifica estan en `notebooks/06_consultas_analisis_cientifico.ipynb`. Ejemplo:

```python
%pip install mysql-connector-python

import mysql.connector

conn = mysql.connector.connect(
    host="mysql",
    port=3306,
    user="root",
    password="root",
    database="optica_y_fotonica",
)

cursor = conn.cursor()
cursor.execute("SELECT VERSION();")
print(cursor.fetchone())
cursor.close()
conn.close()
```

Si cambias el `.env`, actualiza tambien estas credenciales en el notebook.

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
