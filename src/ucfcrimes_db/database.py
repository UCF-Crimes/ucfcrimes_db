import csv
from configparser import SectionProxy
from contextlib import closing
from datetime import date
from pathlib import Path
from tempfile import NamedTemporaryFile

import psycopg2
from psycopg2 import sql

from .geocoding import address_to_place, google_geocoder
from .pdf import CrimeReport


def connect(settings: SectionProxy):
    return psycopg2.connect(
        host=settings["host"],
        port=settings.getint("port", fallback=None),
        dbname=settings["database"],
        user=settings["user"],
        password=settings["password"],
    )


def table_identifier(cursor, table: str) -> sql.Identifier:
    cursor.execute("SELECT parse_ident(%s)", (table,))
    return sql.Identifier(*cursor.fetchone()[0])


def save_cases(settings: SectionProxy, cases: list[CrimeReport], api_key: str) -> None:
    with closing(connect(settings)) as connection, connection.cursor() as cursor:
        table = table_identifier(cursor, settings.get("table", "crimes"))
        update = sql.SQL("""
            UPDATE {}
            SET title = %(title)s, campus = %(campus)s, disposition = %(disposition)s,
                report_dt = %(report_dt)s, start_dt = %(start_dt)s, end_dt = %(end_dt)s, address = %(address)s
            WHERE case_id = %(case_id)s
        """).format(table)
        columns = ("case_id", "title", "campus", "disposition", "report_dt", "start_dt", "end_dt", "address", "place")
        insert = sql.SQL("INSERT INTO {} ({}) VALUES ({})")
        inserts = {
            column_set: insert.format(
                table,
                sql.SQL(", ").join(map(sql.Identifier, column_set)),
                sql.SQL(", ").join(map(sql.Placeholder, column_set)),
            )
            for column_set in (columns, columns + ("lat", "lng"))
        }

        for case in cases:
            with connection:
                # Serialize competing imports of the same case without changing the live schema.
                cursor.execute(
                    "SELECT pg_advisory_xact_lock(hashtext('ucfcrimes_db'), hashtext(%s))", (case["case_id"],)
                )
                cursor.execute(update, case)
                if cursor.rowcount:
                    continue

                address = case["address"]
                lat, lng = google_geocoder(f"{address}, ORLANDO, FL", api_key)
                place = address_to_place(address, lat, lng, api_key)
                if lat is None or lng is None:
                    cursor.execute(inserts[columns], {**case, "place": place})
                else:
                    cursor.execute(inserts[columns + ("lat", "lng")], {**case, "place": place, "lat": lat, "lng": lng})


def backup_crimes(settings: SectionProxy, backup_dir: Path) -> Path:
    backup_dir.mkdir(parents=True, exist_ok=True)
    destination = backup_dir / f"crimes-{date.today():%m-%d-%Y}.csv"

    with closing(connect(settings)) as connection, connection.cursor() as cursor:
        table = table_identifier(cursor, settings.get("table", "crimes"))
        cursor.execute(sql.SQL("SELECT * FROM {}").format(table))
        with NamedTemporaryFile(mode="w", encoding="utf-8", newline="", dir=backup_dir, delete=False) as output:
            temporary = Path(output.name)
            try:
                writer = csv.writer(output)
                writer.writerow(("", *(column.name for column in cursor.description)))
                for index, row in enumerate(cursor):
                    writer.writerow((index, *row))
                output.close()
                temporary.replace(destination)
            finally:
                temporary.unlink(missing_ok=True)
    return destination
