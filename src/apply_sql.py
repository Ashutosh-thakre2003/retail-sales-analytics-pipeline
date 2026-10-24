"""Apply one or more SQL files to the warehouse.

Usage:
    python src/apply_sql.py sql/schema.sql
    python src/apply_sql.py sql/views.sql

When POWERBI_PASSWORD is set and sql/views.sql is applied, a read-only
role (powerbi_reader) is created or updated with SELECT access to the
reporting schema only.
"""

import os
import sys
from pathlib import Path

from psycopg import sql

import db

READER_ROLE = "powerbi_reader"


def grant_reader(cur, password):
    cur.execute(
        "SELECT 1 FROM pg_roles WHERE rolname = %s", (READER_ROLE,)
    )
    verb = "ALTER" if cur.fetchone() else "CREATE"
    cur.execute(
        sql.SQL("{} ROLE {} WITH LOGIN PASSWORD {}").format(
            sql.SQL(verb),
            sql.Identifier(READER_ROLE),
            sql.Literal(password),
        )
    )
    role = sql.Identifier(READER_ROLE)
    cur.execute(
        sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(
            sql.Identifier(db.DB_NAME), role
        )
    )
    cur.execute(sql.SQL("GRANT USAGE ON SCHEMA reporting TO {}").format(role))
    cur.execute(
        sql.SQL("GRANT SELECT ON ALL TABLES IN SCHEMA reporting TO {}").format(role)
    )
    # Views read analytics tables with the owner's rights, so the reader
    # needs no access to the analytics schema itself.
    print(f"Read-only role '{READER_ROLE}' granted SELECT on reporting.*")


def main(paths):
    if not paths:
        raise SystemExit("Usage: python src/apply_sql.py <file.sql> [...]")

    with db.connect() as conn:
        with conn.cursor() as cur:
            for path in paths:
                statements = Path(path).read_text(encoding="utf-8")
                cur.execute(statements)
                print(f"Applied {path}")

                reader_password = os.environ.get("POWERBI_PASSWORD")
                if Path(path).name == "views.sql" and reader_password:
                    grant_reader(cur, reader_password)


if __name__ == "__main__":
    main(sys.argv[1:])
