from configparser import SectionProxy
from contextlib import closing

import psycopg2
from psycopg2 import sql

from .pdf import COLUMNS


def connect(settings: SectionProxy):
    return psycopg2.connect(
        host=settings["host"],
        port=settings.getint("port", fallback=None),
        dbname=settings["database"],
        user=settings["user"],
        password=settings["password"],
    )


def latest_case_id(settings: SectionProxy) -> str | None:
    with closing(connect(settings)) as connection, connection.cursor() as cursor:
        cursor.execute(
            sql.SQL("SELECT case_id FROM {} ORDER BY id DESC LIMIT 1").format(
                table_identifier(cursor, settings["table"])
            )
        )
        row = cursor.fetchone()
        return row[0] if row else None


def table_identifier(cursor, table: str) -> sql.Identifier:
    cursor.execute("SELECT parse_ident(%s)", (table,))
    return sql.Identifier(*cursor.fetchone()[0])


def insert_cases(settings: SectionProxy, cases: list[dict[str, str]]) -> None:
    with closing(connect(settings)) as connection, connection, connection.cursor() as cursor:
        query = sql.SQL("INSERT INTO {} ({}) VALUES ({})").format(
            table_identifier(cursor, settings["table"]),
            sql.SQL(", ").join(map(sql.Identifier, COLUMNS)),
            sql.SQL(", ").join(sql.Placeholder() for _ in COLUMNS),
        )
        cursor.executemany(query, [tuple(case[column] for column in COLUMNS) for case in cases])
