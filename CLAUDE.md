# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

PJECZ Hércules — BETA version of a Flask web application for the Poder Judicial del Estado de Coahuila de
Zaragoza, used to trial new modules before they land in the main Hércules system. Python 3.14, Flask 3.1,
PostgreSQL via SQLAlchemy 2.0 (`Mapped`/`mapped_column` style), Flask-Login, Flask-WTF, Bootstrap frontend
with server-rendered Jinja2 templates and DataTables for listings. Deployed on Google Cloud (App Engine +
Cloud Storage + Secret Manager) via Gunicorn/Uvicorn.

## Commands

Package management is via **uv** (`uv.lock` is authoritative; `requirements.txt` is auto-exported from it —
regenerate with `uv export --format requirements-txt --output-file requirements.txt`, don't hand-edit it).

```bash
uv sync                        # install/sync dependencies into .venv
uv run python main.py          # run the dev server (uvicorn, host/port from .env, auto-reload)
uv run python cli/app.py --help        # Typer CLI: db seeding/backup/copy, autoridades, modulos, ofi_documentos, ofi_plantillas, usuarios
uv run python cli/app.py db alimentar  # example: seed the DB from seed/*.csv
uvx ruff check .                # lint (ignores F821 per pyproject.toml)
uvx black .                     # format (line-length 128, see pyproject.toml)
uvx isort .                     # import sorting (black profile, line-length 128)
uvx basedpyright                # type checking (basic mode, tests/ excluded)
```

There is currently no automated test suite (`tests/` only contains an empty `__init__.py`) — verify changes
by running the dev server and exercising the affected views/CLI commands manually.

Configuration lives in `.env` (never commit it — see `.gitignore`). It documents the required variables
inline (DB connection, `SECRET_KEY`, `SALT`, Google Cloud Storage buckets per module, Redis/RQ task queue,
e-firma and SendGrid credentials, etc.).

## Architecture

### App assembly

`pjecz_hercules_beta_flask/app.py` is the single composition root: it imports every blueprint's `views`
module, registers each with `app.register_blueprint(...)`, then initializes the shared extensions
(`csrf`, `database`, `login_manager`, `moment` from `config/extensions.py`) and wires up Flask-Login via
`authentication(Usuario)`. `main.py` loads `.env` and runs this app with `uvicorn` for local development;
`cli/app.py` is a separate Typer entry point that imports models/`database` directly for maintenance tasks
(seeding, backups, prod→dev copies) without booting the web server.

### Blueprint-per-module structure

Every feature lives under `pjecz_hercules_beta_flask/blueprints/<modulo>/` with a consistent shape:

```
<modulo>/
├── __init__.py
├── models.py                    # SQLAlchemy model(s), inherits UniversalMixin
├── forms.py                     # Flask-WTF forms
├── views.py                     # Blueprint + routes
├── decorators.py                # (only in a few modules, e.g. usuarios) auth/permission decorators
├── tasks.py                     # (only where async/RQ work is needed)
└── templates/<modulo>/*.jinja2
```

There are no cross-module blueprints by file type — routes always live in the owning module's `views.py`,
never loose in `app.py`. Module name prefixes (e.g. `arc_`, `exh_`, `ofi_`, `soportes_`, `vsp_`) group
related sub-modules (archivo, exhortos, oficialía de partes, soportes/tickets, ventanilla).

### Data layer (`lib/universal_mixin.py`)

Every model mixes in `UniversalMixin`, which supplies:
- `creado` / `modificado` timestamps and an `estatus` char column (`"A"` active / `"B"` borrado).
- `save()` — the only way to persist: `database.session.add(self)` + `commit()`.
- `delete()` / `recover()` — soft delete/restore by flipping `estatus`, not row deletion.
- `encode_id()` / `decode_id()` — Hashids-based obfuscated IDs (salt from `Settings.SALT`) used in URLs.

Convention: instantiate the model with its columns, then call `.save()`; to update, mutate attributes then
call `.save()` again. Never call `db.session.commit()` directly in views/CLI — go through `save()`.

### Auth and permissions

Permissions are modeled as `Modulo` × `Rol` → `Permiso` (levels `VER`=1, `MODIFICAR`=2, `CREAR`=3 (shares
value with `BORRAR`), `ADMINISTRAR`=4 — see `blueprints/permisos/models.py`), assigned to a `Usuario` via
`UsuarioRol`. Every blueprint gates access with a `before_request` hook stacking `@login_required` and
`@permission_required(MODULO, Permiso.<NIVEL>)` (from `blueprints/usuarios/decorators.py`), where `MODULO`
is a module-name constant defined at the top of `views.py` matching a row in the `modulos` table/`seed/modulos.csv`.

### Listings: DataTables convention

List views follow a fixed pair-of-routes pattern (see `blueprints/entradas_salidas/views.py` for a compact
example): a `GET /<modulo>` route renders the Jinja2 list shell with a JSON-encoded `filtros` dict, and a
`/<modulo>/datatable_json` route (`get_datatable_parameters()` / `output_datatable_json()` from
`lib/datatables.py`) does the actual filtered/paginated SQLAlchemy query and returns the DataTables JSON
shape (`draw`, `iTotalRecords`, `iTotalDisplayRecords`, `aaData`).

### Settings & secrets

`config/settings.py`'s `get_secret()` resolves each setting from the environment when `PROJECT_ID` is unset
(local dev), otherwise from Google Cloud Secret Manager under `<SERVICE_PREFIX>_<secret_id>` — falling back
to the given default if either lookup fails. `Settings` (pydantic-settings `BaseSettings`) overrides source
precedence so real env vars win over `.env`/file secrets. Never hardcode credentials — add a new `get_secret`
entry and document it in `.env`'s comments instead.

### Other shared libs (`pjecz_hercules_beta_flask/lib/`)

- `safe_string.py` — regexes and sanitizers (`safe_clave`, `safe_email`, expediente parsing, etc.) for
  validating/cleaning user input; prefer these over ad-hoc regex in views/forms.
- `google_cloud_storage.py` / `storage.py` — per-module Cloud Storage bucket helpers (each module that
  stores files, e.g. edictos/glosas/sentencias/exhortos, has its own `CLOUD_STORAGE_DEPOSITO_*` bucket).
- `tasks.py` — RQ (Redis Queue) task helpers for async work.
- `pwgen.py`, `cryptography.py` — password generation and Fernet-based encryption helpers.

### Seed data

`seed/*.csv` holds bootstrap data (catálogos like estados/municipios/materias, plus autoridades, oficinas,
usuarios/roles) loaded by the `cli/app.py db alimentar*` commands — used to populate a fresh database.

## Conventions

- PEP 8; ignore F821 (undefined names — common false positive in models/views due to string-quoted
  relationship type hints); max line length 128.
- Classes: PascalCase with a module-derived three-letter-ish prefix where the module has one (e.g.
  `OfiPlantilla`, `ArcDocumento`). Variables/functions/routes: snake_case.
- Blueprints organized strictly by module, not by file type — don't add routes to `app.py`.

## What Claude must NOT do

- Don't run `flask run` in production mode.
- Don't call `db.drop_all()` / `db.create_all()` in production code paths.
- Don't hardcode passwords, tokens, or connection URIs — use `get_secret`/`.env`.
- Don't swallow database errors without a rollback.
- Don't create routes outside of a blueprint's `views.py`.
