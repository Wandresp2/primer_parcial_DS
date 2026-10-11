"""Conexion MySQL para la app Streamlit (host Docker: mysql)."""

from __future__ import annotations

import os
from functools import lru_cache

import pandas as pd
import sqlalchemy as sa
from sqlalchemy import bindparam, text


def mysql_config() -> dict:
    return {
        "host": os.getenv("MYSQL_HOST", "mysql"),
        "port": int(os.getenv("MYSQL_PORT", "3306")),
        "user": os.getenv("MYSQL_USER", "root"),
        "password": os.getenv("MYSQL_PASSWORD", "root"),
        "database": os.getenv("MYSQL_DATABASE", "optica_y_fotonica"),
    }


@lru_cache(maxsize=1)
def get_engine() -> sa.Engine:
    cfg = mysql_config()
    url = (
        f"mysql+pymysql://{cfg['user']}:{cfg['password']}"
        f"@{cfg['host']}:{cfg['port']}/{cfg['database']}"
    )
    return sa.create_engine(url, pool_pre_ping=True)


def read_sql(sql: str, params: dict | None = None) -> pd.DataFrame:
    params = params or {}
    stmt = text(sql)
    expanding = [
        bindparam(k, expanding=True)
        for k, v in params.items()
        if isinstance(v, (list, tuple))
    ]
    if expanding:
        stmt = stmt.bindparams(*expanding)
    with get_engine().connect() as conn:
        return pd.read_sql(stmt, conn, params=params)


def ping() -> tuple[bool, str]:
    try:
        with get_engine().connect() as conn:
            version = conn.execute(text("SELECT VERSION()")).scalar()
            n = conn.execute(text("SELECT COUNT(*) FROM linea_espectral")).scalar()
        return True, f"MySQL {version} · {n:,} líneas en linea_espectral"
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)
