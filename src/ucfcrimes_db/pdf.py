"""Parse the UCF Police Daily Crime Log.

Based on the monorepo parser written by Ethan Frakes.
"""

import re
from datetime import datetime
from io import BytesIO
from typing import TypedDict

import requests
from pypdf import PdfReader

DAILY_LOG_URL = "https://police.ucf.edu/wp-content/uploads/clery/ALL%20DAILY%20crime%20log.pdf"
CAMPUS_STARTS = ("MAIN", "UCF", "ROSEN")
DISPOSITIONS = ("UNFOUNDED", "EXC", "ARREST", "INACTIVE", "CLOSED", "OPEN", "ACTIVE", "REPORT")
CASE_ID = re.compile(r"\d{4}-(?:\d{4}|[A-Za-z]{3}\d{2})")
TITLE_WORDS = re.compile(r"\b(?:TRAFFIC|TRESPASSING|DRUG|LAW|WARRANT)\b")
JOINED_COLUMN = re.compile(r"(?<=\S)(?:" + "|".join(CAMPUS_STARTS + DISPOSITIONS) + ")")
JOINED_ROSEN_COLUMN = re.compile(r"(?:HOSPITALITY|MANAGEMENT)(?=\S)")
DATE_FORMATS = ("%m/%d/%y", "%m/%d/%Y")


class CrimeReport(TypedDict):
    case_id: str
    title: str
    campus: str
    disposition: str
    report_dt: str
    start_dt: str
    end_dt: str
    address: str


def parse_date(value: str) -> datetime:
    for date_format in DATE_FORMATS:
        try:
            return datetime.strptime(value, date_format)
        except ValueError:
            continue
    raise ValueError(f"Invalid date: {value!r}")


def is_date(value: str) -> bool:
    try:
        parse_date(value)
    except ValueError:
        return False
    return True


def format_timestamp(day: str, clock: str) -> str:
    timestamp = datetime.combine(parse_date(day).date(), datetime.strptime(clock, "%H:%M").time())
    return timestamp.strftime("%Y-%m-%dT%H:%M:%SZ")


def tokenize_page(text: str) -> list[list[str]]:
    text = JOINED_COLUMN.sub(r" \g<0>", text)
    text = JOINED_ROSEN_COLUMN.sub(r"\g<0> ", text)

    rows = []
    current = []
    for token in text.split():
        if CASE_ID.fullmatch(token):
            if current:
                rows.append(current)
            current = [token]
        elif current:
            current.append(token)
    if current:
        rows.append(current)
    return rows


def parse_case(tokens: list[str]) -> CrimeReport:
    title_end = 2
    while tokens[title_end] not in CAMPUS_STARTS:
        if tokens[title_end] in DISPOSITIONS and not TITLE_WORDS.search(" ".join(tokens[1:title_end])):
            break
        title_end += 1

    if tokens[title_end] in DISPOSITIONS:
        campus = "UNSPECIFIED CAMPUS"
        disposition_start = title_end
    else:
        disposition_start = title_end + 1
        while tokens[disposition_start] not in DISPOSITIONS:
            disposition_start += 1
        campus = " ".join(tokens[title_end:disposition_start])

    date_start = disposition_start + 1
    while not is_date(tokens[date_start]):
        date_start += 1

    report_day, report_time, start_day, start_time, end_day, end_time = tokens[date_start:date_start + 6]
    address = " ".join(tokens[date_start + 6:])
    if not address:
        raise ValueError("Missing address")

    return {
        "case_id": tokens[0],
        "title": " ".join(tokens[1:title_end]),
        "campus": campus,
        "disposition": " ".join(tokens[disposition_start:date_start]),
        "report_dt": format_timestamp(report_day, report_time),
        "start_dt": format_timestamp(start_day, start_time),
        "end_dt": format_timestamp(end_day, end_time),
        "address": address,
    }


def parse_pdf(content: bytes) -> list[CrimeReport]:
    reader = PdfReader(BytesIO(content))
    cases = []
    for page in reader.pages:
        for tokens in tokenize_page(page.extract_text() or ""):
            try:
                cases.append(parse_case(tokens))
            except (IndexError, ValueError):
                print(f"Skipping incomplete or invalid report {tokens[0]}")

    if not cases:
        raise ValueError("The daily crime log contained no cases in the expected format.")
    return cases


def crime_load() -> list[CrimeReport]:
    response = requests.get(DAILY_LOG_URL, timeout=30)
    response.raise_for_status()
    return parse_pdf(response.content)
