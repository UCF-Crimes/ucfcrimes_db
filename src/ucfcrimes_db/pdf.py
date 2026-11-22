'''

UCF Crimes: loadcrimes.py
Written by Ethan Frakes

'''

from datetime import datetime
from io import BytesIO

import requests
from PyPDF2 import PdfReader


# Returns if date string token passed is valid.
def is_valid_date(date_string: str) -> bool:
    # First is for mm/dd/yy and second is for mm/dd/yyyy
    valid_formats = ['%m/%d/%y', '%m/%d/%Y']
    for date_format in valid_formats:
        try:
            datetime.strptime(date_string, date_format)
            return True
        except ValueError:
            pass
    return False

# Returns if time string token passed is valid.
def is_valid_time_label(time_str: str) -> bool:
    try:
        datetime.strptime(time_str, '%H:%M')
        return True
    except ValueError:
        return False

# Tokenizes each crime into separate elements of a 2D string array, where each 1st dimension
# element is each crime and each 2nd dimension element is each space/newline delimited string.
def tokenizer(page) -> list:

    # Text extracted from page and split between spaces and newlines.
    crime_list = []
    text = page.extract_text()
    textToken = text.split()
    buffer_list = []
    valid_delimiters = ["Incident", "UNFOUNDED", "EXC", "ARREST", "INACTIVE",
                        "CLOSED", "OPEN", "ACTIVE", "REPORT"]

    # For each string in the textToken, if the string is one of the valid delimiters above
    # (end of one crime and beginning of another), buffer list is added to the crime list.
    for elem in range(len(textToken)):
        for delimiter in valid_delimiters:
            if delimiter == "ARREST" and textToken[elem] == delimiter and textToken[elem + 1:elem + 2] == ["-"]:
                crime_list.append(buffer_list)
                buffer_list = []

            elif delimiter != "ARREST" and textToken[elem] == delimiter:
                crime_list.append(buffer_list)
                buffer_list = []

        buffer_list.append(textToken[elem])

    crime_list.append(buffer_list)
    return crime_list

# Parses each crime element by grouping unjoined tokens together that correspond to the same
# dictionary key.
def parser(crime_list: list) -> list:
    crime_list_len = len(crime_list)

    for i in range(crime_list_len):
        for j, elem in enumerate(crime_list[i]):
            if elem == "ARREST":
                crime_list[i][j] += " " + crime_list[i][j+1] + " " + crime_list[i][j+2]
                crime_list[i].remove(crime_list[i][j+1])
                crime_list[i].remove(crime_list[i][j+1])

            elif elem == "EXC":
                crime_list[i][j] += " " + crime_list[i][j+1] + " " + crime_list[i][j+2] + " " + crime_list[i][j+3]
                crime_list[i].remove(crime_list[i][j+1])
                crime_list[i].remove(crime_list[i][j+1])
                crime_list[i].remove(crime_list[i][j+1])

            elif is_valid_time_label(crime_list[i][j]):
                j += 1
                while j + 1 < len(crime_list[i]) and not is_valid_date(crime_list[i][j+1]) and not is_valid_time_label(crime_list[i][j+1]):
                    crime_list[i][j] += " " + crime_list[i][j+1]
                    crime_list[i].remove(crime_list[i][j+1])

        try:
            if is_valid_date(crime_list[i][4][-8:]):
                    crime_list[i].insert(5, crime_list[i][4][-8:])
                    crime_list[i][4] = crime_list[i][4][:-8].strip()
        except IndexError: pass

        if len(crime_list[i]) == 10 and is_valid_time_label(crime_list[i][-1]):
            crime_list[i].append("UNSPECIFIED CAMPUS")

        if len(crime_list[i]) == 11:
            crime_list[i][2] += " " + crime_list[i][3]
            crime_list[i][5] += " " + crime_list[i][6]
            crime_list[i][8] += " " + crime_list[i][9]
            del crime_list[i][3]
            del crime_list[i][5]
            del crime_list[i][7]

    return crime_list

COLUMNS = ("disposition", "case_id", "report_dt", "crime", "start_dt", "location", "end_dt", "campus")
DAILY_LOG_URL = "https://police.ucf.edu/sites/default/files/logs/ALL%20DAILY%20crime%20log.pdf"


def crime_load() -> list[dict[str, str]]:
    response = requests.get(DAILY_LOG_URL, timeout=30)
    response.raise_for_status()
    reader = PdfReader(BytesIO(response.content))

    cases = []
    for page in reader.pages:
        for row in parser(tokenizer(page)):
            if len(row) == len(COLUMNS):
                cases.append(dict(zip(COLUMNS, row)))
    return cases
