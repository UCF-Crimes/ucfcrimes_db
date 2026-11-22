import argparse
from configparser import ConfigParser
from datetime import datetime, timedelta
from pathlib import Path
from time import sleep

from .database import backup_crimes, save_cases
from .pdf import crime_load


def next_run_time(now: datetime) -> datetime:
    return (now + timedelta(days=1)).replace(hour=0, minute=3, second=0, microsecond=0)


def import_crimes(config: ConfigParser) -> None:
    database = config["postgresql"] if config.has_section("postgresql") else config["POSTGRESQL"]
    api_key = config.get(
        "geocoding", "google_maps_api_key", fallback=config.get("DISCORD", "gmaps_api_key", fallback="")
    )
    cases = crime_load()
    save_cases(database, cases, api_key)
    print(f"Imported {len(cases)} reports into PostgreSQL.")
    backup = backup_crimes(database, Path("backups"))
    print(f"Crime CSV backed up to {backup}.")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Update PostgreSQL from the UCF Police Daily Crime Log.")
    parser.add_argument("--config", type=Path, default=Path("config.ini"), help="Path to the INI configuration")
    parser.add_argument("--once", action="store_true", help="Import once and exit")
    options = parser.parse_args(argv)

    config = ConfigParser(interpolation=None)
    with options.config.open(encoding="utf-8") as config_file:
        config.read_file(config_file)

    while True:
        import_crimes(config)
        if options.once:
            return

        now = datetime.now()
        target_time = next_run_time(now)
        print(f"Sleeping until {target_time}")
        sleep((target_time - now).total_seconds())
