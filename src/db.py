"""Shared database connection settings.

Values come from environment variables (set by compose.yaml inside the
Spark container). Defaults match the Docker Compose service names.
"""

import os

import psycopg

DB_HOST = os.environ.get("DB_HOST", "postgres")
DB_PORT = int(os.environ.get("DB_PORT", "5432"))
DB_NAME = os.environ.get("DB_NAME", "retail_analytics")
DB_USER = os.environ.get("DB_USER", "retail_user")


def db_password():
    password = os.environ.get("DB_PASSWORD")
    if not password:
        raise RuntimeError(
            "DB_PASSWORD is not set. Set POSTGRES_PASSWORD in .env and "
            "run the scripts inside the retail_spark container."
        )
    return password


def jdbc_url():
    return f"jdbc:postgresql://{DB_HOST}:{DB_PORT}/{DB_NAME}"


def sqlalchemy_url():
    return (
        f"postgresql+psycopg://{DB_USER}:{db_password()}"
        f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )


def connect():
    return psycopg.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=db_password(),
    )
