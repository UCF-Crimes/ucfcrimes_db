# UCF Crimes database loader

Imports the [UCF Police Daily Crime Log](https://police.ucf.edu/clery-act/daily-crime-log/) into the PostgreSQL table used by the UCF Crimes publishers. A run inserts new cases, updates existing cases by `case_id`, and writes a daily CSV snapshot under `backups/`.

## Setup

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install .
cp config.example.ini config.ini
```

Set the database connection details in `config.ini`. By default the loader uses the existing `crimes` table with `case_id`, `title`, `campus`, `disposition`, `report_dt`, `start_dt`, `end_dt`, `address`, `place`, `lat`, and `lng` columns. The publishers expect the date fields in ISO timestamp format. The earlier `cases` table uses a different schema.

Set `google_maps_api_key` to enable Google geocoding for new cases. The loader also supports the monorepo's `[POSTGRESQL]` section and `[DISCORD]` section's `GMAPS_API_KEY`. Set `table = crimes` if the copied configuration contains a placeholder table name.

## Run

```sh
ucfcrimes-db --config config.ini --once
```

Use `--once` for cron or another external scheduler. With no `--once` flag, the loader runs on startup and again daily at 12:03 a.m. in the host's local time. Both modes are also available via `python -m ucfcrimes_db`.

### Disclaimers
UCF Crimes gathers data from the UCFPD daily crime log and posts information to Instagram and Discord. Incidents are made public according to the Clery Act, a federal law that requires all U.S. colleges and universities (including foreign campuses of U.S. institutions), both public and private, to participate in federal student aid programs to maintain and disclose certain crime statistics and campus security/fire information. All information republished by UCF Crimes is gathered directly from the UCFPD daily crime log, and no erroneous or false information is injected into the posts.

- UCF Crimes is not affiliated with UCFPD
- UCF Crimes is not created with malicious intent
- UCF Crimes does not encourage malicious behavior of any kind

## Connect

- IG: [@UCFcrimes](https://www.instagram.com/ucfcrimes/)
- Facebook: [@UCFcrimes](https://www.facebook.com/ucfcrimes)
- Discord: [UCF Crimes](https://discord.gg/NEEbsbu8Np)
