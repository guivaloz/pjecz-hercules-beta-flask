---
name: flask-crud
description: Generate the standard CRUD routes in views.py (datatable_json, list_active, list_inactive, detail, new, edit, delete, recover), the WTForm in forms.py, and the list, detail, new and edit Jinja2 templates for a catalog blueprint. Supports integer or UUID primary keys and second-level blueprints that depend on a parent (e.g. oficinas → distritos). Use it when the user asks to create the views/templates of a basic catalog blueprint.
argument-hint: 'blueprint name, e.g. exh_areas'
allowed-tools: Read, Glob, Grep, Write, Edit, AskUserQuestion, Bash(ls:*), Bash(cat:*)
---

# /flask-crud — Standard catalog routes and templates

Generates a complete catalog blueprint (the "basic catalog" pattern) for `pjecz_hercules_beta_flask`:

- `forms.py` with `<Model>Form`
- `views.py` with the 8 standard routes, in this order: `datatable_json`, `list_active`, `list_inactive`, `detail`, `new`, `edit`, `delete`, `recover`
- `templates/<blueprint>/list.jinja2`, `detail.jinja2`, `new.jinja2`, `edit.jinja2`

The canonical code lives in the files next to this skill. **Read the ones you need before writing anything**:

| File | Use |
|---|---|
| `views-int.py.tmpl` | `views.py` when the primary key is an integer |
| `views-uuid.py.tmpl` | `views.py` when the primary key is a UUID |
| `forms.py.tmpl` | `forms.py`, with the variants for a parent `SelectField` (int or UUID) |
| `list.jinja2` | List template |
| `detail.jinja2` | Detail template, with the optional block for an embedded child DataTable |
| `new.jinja2` | New template |
| `edit.jinja2` | Edit template |

## Reference blueprints in this repo

When in doubt, read the real code under `src/pjecz_hercules_beta_flask/blueprints/`:

- **First level, int id**: `distritos`, `domicilios`, `materias`, `modulos`, `roles`
- **First level, UUID id**: `dgt_tipos`, `dgt_depositos`
- **Second level (depend on a parent)**: `autoridades` (→ distritos, materias), `oficinas` (→ distritos, domicilios), `dgt_rutas` (→ dgt_depositos, dgt_tipos, UUID)

## When to use

- The blueprint directory already exists and has a `models.py` with the model (use `flask-models` first otherwise)
- The user wants the full set of catalog routes and templates

Do NOT use it to modify an existing `views.py` that already has these routes; in that case edit only what is missing.

## Workflow

1. Read `src/pjecz_hercules_beta_flask/blueprints/<blueprint>/models.py`: class name, `__tablename__`, primary key type (`Mapped[int]` vs `Mapped[uuid.UUID]`), columns, foreign keys (`ForeignKey(...)`) and relationships.
2. Determine the variant:
   - **Primary key**: `int` → `views-int.py.tmpl`; `uuid.UUID` → `views-uuid.py.tmpl`.
   - **Level**: if the model has `ForeignKey` columns to other catalogs, it is second level; each parent becomes a `SelectField` in the form, an id filter in `datatable_json`, a flattened column in the DataTable, and a link in the detail.
3. Determine the `MODULO`: uppercase, may have spaces (e.g. `DGT DEPOSITOS`). Look it up in `seed/modulos.csv` (column `nombre`) if the file exists, or in any template/view that already references the module (`grep -rn "can_view('<MODULO>" src`). If not found, propose the uppercase blueprint name with spaces instead of underscores and confirm with the user.
4. Ask the user only what cannot be inferred from the model (use `AskUserQuestion`, one round at most):
   - Display names, singular/plural and grammatical gender (`Nuevo Distrito` / `Nueva Oficina`, `activos` / `activas`)
   - Which column is the link/identifier (usually `clave`, otherwise `nombre`/`descripcion`)
   - Which columns are unique (validated in `new`/`edit`), which are shown in the list and which are filterable
   Propose sensible defaults derived from the model so the user just confirms.
5. Generate `forms.py`, `views.py` and the four templates by filling in the placeholders.
6. If it is second level, offer to add the embedded child DataTable to the **parent's** `detail.jinja2` (see "Second level" below). Do it only if the user agrees.
7. Finish with the checklist in "After creating the files".

## Placeholders

| Placeholder | Meaning | Example (int) | Example (UUID) |
|---|---|---|---|
| `<blueprint>` | Blueprint dir/name, plural snake_case | `distritos` | `dgt_depositos` |
| `<Model>` | Model class | `Distrito` | `DgtDepositos` |
| `<singular>` | Instance variable, singular snake_case | `distrito` | `dgt_deposito` |
| `<Singular>` | Display name, singular | `Distrito` | `DGT Depósito` |
| `<Plural>` | Display name, plural | `Distritos` | `DGT Depósitos` |
| `<PluralCamel>` | Plural PascalCase for JS identifiers | `Distritos` | `DgtDepositos` |
| `<SingularCamel>` | Singular PascalCase for filter input ids | `Distrito` | `DgtDeposito` |
| `<MODULO>` | Permission module, as in `seed/modulos.csv` | `DISTRITOS` | `DGT DEPOSITOS` |
| `<un>` | Article matching gender | `un` | `un` |
| `<Nuevo>` | `Nuevo` / `Nueva` | `Nuevo` | `Nuevo` |
| `<activos>` | `activos` / `activas` | `activos` | `activos` |
| `<inactivos>` | `inactivos` / `inactivas` | `inactivos` | `inactivos` |
| `<link_column>` | Identifier column (link in list, big value in detail, bitácora text) | `clave` | `clave` |
| `<order_column>` | Column for `order_by` (usually = `<link_column>`) | `clave` | `clave` |

For parents (second level): `<parent>` (e.g. `distrito`), `<parent_blueprint>` (`distritos`), `<Parent>` (`Distrito`), `<PARENT_MODULO>` (`DISTRITOS`), `<parent_label_column>` (column shown in the select/detail, e.g. `nombre_corto`).

## Rules for views.py

- Module docstring: `"""<Plural>, vistas"""`. Function docstrings follow the templates and respect gender: `"""Detalle de una Oficina"""`, `"""Listado de Oficinas activas"""`, `"""Nueva Oficina"""`.
- `before_request` always: `@login_required` + `@permission_required(MODULO, Permiso.VER)`.
- Permissions per route: `list_inactive`, `delete`, `recover` → `Permiso.ADMINISTRAR`; `new` → `Permiso.CREAR`; `edit` → `Permiso.MODIFICAR`.
- Routes: `/<blueprint>`, `/<blueprint>/inactivos`, `/<blueprint>/<id>`, `/<blueprint>/nuevo`, `/<blueprint>/edicion/<id>`, `/<blueprint>/eliminar/<id>`, `/<blueprint>/recuperar/<id>`, `/<blueprint>/datatable_json`.
- **int**: route converter `<int:<singular>_id>` and `Model.query.get_or_404(<singular>_id)`.
- **UUID**: route converter `<<singular>_id>` (no converter) and, in `detail`, `edit`, `delete` and `recover`, validate first with `safe_uuid`; if it returns `""`, `flash("ID de <Singular> inválido", "warning")` and redirect to `list_active`. Import `safe_uuid`.
- Keep the Spanish section comments exactly: `# Tomar parámetros de Datatables`, `# Consultar`, `# Primero filtrar por columnas propias`, `# Luego filtrar por columnas de otras tablas`, `# Ordenar y paginar`, `# Elaborar datos para DataTable`, `# Entregar JSON`.
- In `datatable_json` the loop variable is `resultado`; the first key of each row is `"detalle"` with `<link_column>` and `url`; parent columns are flattened with prefix (`"distrito_clave": resultado.distrito.clave`).
- Sanitize every text input: `safe_clave(..., max_len=N)` for clave-like columns (`N` = column `String` length when it is not 16), `safe_string(..., save_enie=True)` for free text (add `max_len=N` when the column is longer than 256), `safe_email`, `safe_url`, etc. when applicable. Booleans, ints, dates, times and selects go straight from `form.<field>.data`.
- `new` and `edit` validate uniqueness of every `unique=True` column with the `es_valido` pattern; in `edit` only when the value changed and comparing ids.
- Every write (`new`, `edit`, `delete`, `recover`) creates a `Bitacora` with `descripcion=safe_message(f"<Nuevo|Editado|Eliminado|Recuperado> <Singular> {<singular>.<link_column>}")` and `url` to the detail, then `flash(bitacora.descripcion, "success")`.
- `delete` only acts when `estatus == "A"`; `recover` only when `estatus == "B"`. Both always redirect to the detail.
- Import only what is used (`safe_clave` only if there is a clave, `safe_uuid` only for UUID, parent models only if they are joined for filters).

### Filter patterns for datatable_json

The `estatus` filter always goes first. Then, in this order: parent id filters, own text filters, and finally (under `# Luego filtrar por columnas de otras tablas`) joins with parents.

```python
    # Parent id, int
    if "distrito_id" in request.form:
        try:
            distrito_id = int(request.form["distrito_id"])
            consulta = consulta.filter(<Model>.distrito_id == distrito_id)
        except ValueError:
            pass
    # Parent id, UUID
    if "dgt_deposito_id" in request.form:
        dgt_deposito_id = safe_uuid(request.form["dgt_deposito_id"])
        if dgt_deposito_id != "":
            consulta = consulta.filter(<Model>.dgt_deposito_id == dgt_deposito_id)
    # Clave-like column
    if "clave" in request.form:
        try:
            clave = safe_clave(request.form["clave"])
            if clave != "":
                consulta = consulta.filter(<Model>.clave.contains(clave))
        except ValueError:
            pass
    # Free text column
    if "nombre" in request.form:
        nombre = safe_string(request.form["nombre"], save_enie=True)
        if nombre != "":
            consulta = consulta.filter(<Model>.nombre.contains(nombre))
    # Luego filtrar por columnas de otras tablas
    if "distrito_clave" in request.form:
        try:
            distrito_clave = safe_clave(request.form["distrito_clave"])
            if distrito_clave != "":
                consulta = consulta.join(Distrito).filter(Distrito.clave.contains(distrito_clave))
        except ValueError:
            pass
```

## Rules for forms.py

- Docstring `"""<Plural>, formularios"""`, class `<Model>Form` with docstring `"""Formulario <Model>"""`, last field `guardar = SubmitField("Guardar")`.
- Validators: `DataRequired()` for non-nullable columns, `Optional()` for nullable ones and booleans; `Length(max=N)` matching the column `String(N)`; `Regexp(CLAVE_REGEXP)` for 16-char claves.
- Enum columns with a dict of options in the model (e.g. `PROPOSITOS`): `SelectField(..., choices=<Model>.PROPOSITOS.items())`.
- Parents: `SelectField` filled in `__init__` with active parents ordered by the label column. int parent → `coerce=int` and `(d.id, d.<label>)`; UUID parent → `coerce=str` and `(str(d.id), ...)`.

## Rules for templates

- `list.jinja2`: topbar with optional buttons to related catalogs (`topbar.button(label, url, icon)` guarded by `can_view`), the Inactivos/Activos toggle guarded by `can_admin`, and `button_new` guarded by `can_insert`. One filter input per filterable column; `col-*` classes must add up to 12 (buttons cell takes the rest with `text-end`). `<th>` order = `columns` array = `data` keys in `views.py`. Boolean columns render `'SI'` / `''` with a `columnDefs` entry. Long text can be truncated in a `columnDefs` render.
- `detail.jinja2`: topbar with `button_previous` (to `list_active`), `button_edit` (`can_edit`), `button_delete`/`button_recover` (`can_admin`, by estatus). `label_value_big` for `<link_column>`, `label_value` for the rest, `label_value_boolean` for booleans. Parent fields link to the parent detail guarded by `can_view('<PARENT_MODULO>')`. The `custom_javascript` block always includes the delete/recover modals.
- `new.jinja2` / `edit.jinja2`: one `f.form_group(form.<field>)` per form field in the same order as the form, ending with `form.guardar`. `fid='<singular>_form'`. In edit, `form_kwargs = {'<singular>_id': <singular>.id}`.

## Second level

For a blueprint that depends on a parent (e.g. `oficinas` → `distritos`):

1. `forms.py`: a `SelectField` per parent (see above).
2. `views.py`:
   - `datatable_json` accepts `<parent>_id` (int or UUID pattern) and returns flattened `<parent>_clave` (or `<parent>_nombre`).
   - `new`: `<parent>_id=form.<parent>.data`.
   - `edit`: assign `<singular>.<parent>_id = form.<parent>.data` and preload `form.<parent>.data = <singular>.<parent>_id` (int) or `str(<singular>.<parent>_id)` (UUID), with the comment `# Se manda <parent>_id porque es un select`.
3. `list.jinja2`: a column for the parent clave/nombre.
4. `detail.jinja2`: the parent field linked to its detail.
5. **Parent `detail.jinja2`** (optional, ask first): add a card with the embedded child DataTable, filtered by `'<parent>_id': {{ <parent>.id }}` (int) or `'<parent>_id': "{{ <parent>.id }}"` (UUID, with quotes), guarded by `current_user.can_view('<MODULO>') and <parent>.estatus == 'A'`. The block is in `detail.jinja2` next to this skill, marked "Embedded child DataTable". If the parent detail already loads `datatables-constructor.js` and declares `constructorDataTable`, reuse them instead of declaring them twice.

## After creating the files

Check and tell the user what is still pending:

1. The blueprint is registered in `src/pjecz_hercules_beta_flask/main.py`, keeping alphabetical order: `from pjecz_hercules_beta_flask.blueprints.<blueprint>.views import <blueprint>` and `app.register_blueprint(<blueprint>)`.
2. `MODULO` exists in `seed/modulos.csv` (that folder is not versioned; the CSV feeds `pjecz-hercules-beta-flask db inicializar|reiniciar`). If it is a new module, the user must add it there (with `en_navegacion` if it should appear in the menu) and reset the database, or create the module and its permissions from the web app.
3. Format with `black` and `isort` (configured in `pyproject.toml`, line length 128).
