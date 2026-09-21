# JupyterLab + MySQL 8.4 con Docker Compose

Stack de dos contenedores conectados por una red Docker que Compose crea automaticamente (`jupyter_mysql`, driver `bridge`). Desde un notebook se consulta MySQL usando el nombre del servicio (`mysql`), no `localhost`.

Las credenciales estan fijas directamente en `docker-compose.yml` (sin archivo `.env`): no hay ningun paso de configuracion previo, solo levantar el stack.

## Requisitos

- Docker Desktop encendido
- Los puertos **3306** (MySQL) y **8888** (JupyterLab) deben estar **libres** en tu maquina. Si ya hay otro MySQL, XAMPP, MariaDB, otro Jupyter u otro contenedor usando esos puertos, `docker compose up` fallara. Libera esos puertos o cambia el mapeo en `docker-compose.yml` (por ejemplo `"3307:3306"` o `"8889:8888"`).

No necesitas crear la red a mano: Compose la crea al levantar el stack.

## Arranque

1. Levanta los servicios (crea red, volumen y contenedores):

```bash
docker compose up -d
```

2. Abre JupyterLab en [http://localhost:8888](http://localhost:8888) con el token `facil123` (definido en `docker-compose.yml`).

3. Crea la base de datos del proyecto y sus tablas ejecutando `sql/schema.sql` en DBeaver (conectado al servidor MySQL, sin necesidad de una base previa). El script hace `CREATE DATABASE optica_y_fotonica` y luego las 9 tablas vacias. Equivalente por terminal:

```bash
docker exec -i mysql_container mysql -uroot -proot < sql/schema.sql
```

En PowerShell, si la redireccion `<` falla:

```powershell
Get-Content sql/schema.sql -Raw | docker exec -i mysql_container mysql -uroot -proot
```

4. Ejecuta los notebooks en orden desde JupyterLab (carpeta `notebooks/`): `02_exploracion_caracterizacion_datos.ipynb` → `03_limpieza_datos.ipynb` → `04_pipeline_etl_mysql.ipynb` (puebla las 9 tablas) → `05_consultas_analisis_cientifico.ipynb`.

5. Comprueba el estado de los contenedores:

```bash
docker compose ps
```

Compose reutiliza las imagenes locales `mysql:8.4` y `quay.io/jupyter/scipy-notebook:latest` si ya las tienes; si no, las descarga.

## Credenciales (fijas en `docker-compose.yml`)

| Variable | Valor |
|---|---|
| `MYSQL_ROOT_PASSWORD` | `root` |
| `MYSQL_DATABASE` | `optica_y_fotonica` |
| `JUPYTER_TOKEN` | `facil123` |

Nota: en la imagen oficial de MySQL, `MYSQL_USER` no puede ser `root`. Para root usa solo `MYSQL_ROOT_PASSWORD`.

La base de trabajo del proyecto es **`optica_y_fotonica`**. La crea `sql/schema.sql`; el pipeline ETL y los notebooks se conectan a esa base.

## Conexion desde un notebook

Host: `mysql` (nombre del servicio en `docker-compose.yml`). Puerto: `3306`.

Las consultas SQL y la respuesta a la pregunta cientifica estan en `notebooks/05_consultas_analisis_cientifico.ipynb`. La conexion Jupyter → MySQL tambien se usa en `notebooks/04_pipeline_etl_mysql.ipynb`. Ejemplo:

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

Si cambias las credenciales en `docker-compose.yml`, actualiza tambien estos valores en los notebooks.

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

## Estructura del proyecto

```
docker-compose.yml          Definicion de los dos contenedores (MySQL + JupyterLab)
sql/schema.sql               DDL: crea la base y las 9 tablas + 1 vista, vacias
notebooks/                   02 a 05: exploracion, limpieza, ETL y consultas SQL
  datos_originales/          CSV crudos del NIST, sin modificar (evidencia de la fuente)
  datos_procesados/          CSV limpios, generados por los notebooks
docs/                        Documentacion tecnica de cada etapa (02 a 05)
```
