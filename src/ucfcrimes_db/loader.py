import argparse
from configparser import ConfigParser, SectionProxy
from datetime import datetime, timedelta
from pathlib import Path
from time import sleep

from .database import insert_cases, latest_case_id
from .pdf import crime_load


def sync_cases(settings: SectionProxy, previous_case_id: str | None) -> str:
    cases = crime_load()
    if not cases:
        raise ValueError("The daily crime log contained no cases in the expected format.")

    newest_case_id = cases[-1]["case_id"]
    if previous_case_id is None:
        print(f"Started newest case is {newest_case_id}")
        return newest_case_id

    if newest_case_id == previous_case_id:
        return previous_case_id

    for index in range(len(cases) - 1, -1, -1):
        if cases[index]["case_id"] == previous_case_id:
            new_cases = cases[index + 1:]
            insert_cases(settings, new_cases)
            print(f"New cases detected: {len(new_cases)}")
            return newest_case_id

    raise ValueError(f"The previous case {previous_case_id} was absent from the daily crime log.")


def next_run_time(now: datetime) -> datetime:
    return (now + timedelta(days=1)).replace(hour=0, minute=3, second=0, microsecond=0)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Update PostgreSQL from the UCF Police Daily Crime Log.")
    parser.add_argument("--config", type=Path, default=Path("config.ini"), help="Path to the INI configuration")
    options = parser.parse_args(argv)

    config = ConfigParser(interpolation=None)
    with options.config.open(encoding="utf-8") as config_file:
        config.read_file(config_file)
    settings = config["postgresql"]

    previous_case_id = latest_case_id(settings)
    if previous_case_id is not None:
        print(f"Latest case is {previous_case_id}")

    while True:
        previous_case_id = sync_cases(settings, previous_case_id)
        now = datetime.now()
        target_time = next_run_time(now)
        print(f"Sleeping until {target_time}")
        sleep((target_time - now).total_seconds())
