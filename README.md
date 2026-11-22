# UCF Crimes database loader

This loader imports cases from the UCF Police Daily Crime Log into PostgreSQL. It checks on startup, then checks again daily at 12:03 a.m. in the host's local time.

This version expects the original PDF layout. The legacy UCF log URL currently returns HTTP 404, so live ingestion requires the current feed importer.

## Setup

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install .
cp config.example.ini config.ini
```

Fill in the PostgreSQL connection settings and table name in `config.ini`. The existing table uses `id`, `case_id`, `disposition`, `report_dt`, `crime`, `start_dt`, `location`, `end_dt`, and `campus`. The loader uses the highest `id` to pick up where it left off.

```sh
ucfcrimes-db --config config.ini
```

The same command is available as `python -m ucfcrimes_db`. Python source is in `src/ucfcrimes_db/`, and direct dependencies are in `requirements.txt`.

### Disclaimers
UCF Crimes gathers data from the UCFPD daily crime log and posts information to Instagram and Discord. Incidents are made public according to the Clery Act, a federal law that requires all U.S. colleges and universities (including foreign campuses of U.S. institutions), both public and private, to participate in federal student aid programs to maintain and disclose certain crime statistics and campus security/fire information. All information republished by UCF Crimes is gathered directly from the UCFPD daily crime log, and no erroneous or false information is injected into the posts.

- UCF Crimes is not affiliated with UCFPD
- UCF Crimes is not created with malicious intent
- UCF Crimes does not encourage malicious behavior of any kind

## Connect

- IG: [@UCFcrimes](https://www.instagram.com/ucfcrimes/)
- Facebook: [@UCFcrimes](https://www.facebook.com/ucfcrimes)
- Discord: [UCF Crimes](https://discord.gg/NEEbsbu8Np)
