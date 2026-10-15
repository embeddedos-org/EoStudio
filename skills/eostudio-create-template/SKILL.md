---
name: eostudio-create-template
description: Scaffold a new EoStudio project from a built-in template in eostudio/templates/samples.py via create_project_from_template, and extend the catalogue by adding a ProjectTemplate entry to BUILTIN_TEMPLATES. Use when an agent needs to start a project from a template (UI app, CAD part, game, IoT dashboard, dual-brain hardware, PID simulation) or add a new starter template other projects can be created from.
---

# EoStudio Project Templates

Templates are data, not code paths: the catalogue is the
`BUILTIN_TEMPLATES` dict in `eostudio/templates/samples.py`, keyed
by template name, with values of the `ProjectTemplate` dataclass
(`name`, `description`, `category`, `editor_type`, `components`,
`screens`, `metadata`). Everything below goes through the module's
three public functions — never edit a scaffolded project to "fix"
a template; fix the catalogue entry instead.

## Create a project from a template

```python
from eostudio.templates.samples import (
    list_templates, get_template, create_project_from_template,
)

# Discover first: names are the keys every other call takes.
for t in list_templates():            # optionally list_templates(category="ui")
    print(t.name, t.category, t.editor_type)
assert get_template("uno-q-dual-brain") is not None

# Scaffold: returns the path to the created project file.
path = create_project_from_template("uno-q-dual-brain", "out/my-project")
```

`create_project_from_template(template_name, output_dir)` raises
`ValueError` naming the available templates when the name is
unknown — surface that message to the user rather than guessing a
name. The created project is the template's `to_project_dict()`
shape (version, name, description, category, editor_type,
components, screens, metadata) plus a generated README.

The built-in catalogue today:

| Key | Category | Editor |
|---|---|---|
| `todo-app` | ui | ui |
| `mechanical-part` | cad | cad |
| `game-platformer` | game | game |
| `iot-dashboard` | webapp | database |
| `uno-q-dual-brain` | hardware | hardware |
| `simulation-pid` | simulation | simulation |

## Add a new template

Add one entry to `BUILTIN_TEMPLATES` in
`eostudio/templates/samples.py`, in the established shape:

1. **Key and name agree**: the dict key is the template's `name`
   and the scaffold lookup key (`uno-q-dual-brain` is the model).
2. **Description** follows the house style:
   `Name — surface → outcome` (e.g. the dual-brain entry's
   "Linux app + MCU sketch → RPC/Router Bridge project").
3. **Category/editor_type**: reuse an existing category unless the
   template genuinely opens a new one — a new category value is a
   product decision, not a typo fix (`hardware` was introduced
   deliberately, with the dual-brain template).
4. **Components/screens** are plain dicts in the shape the
   neighbouring entries use; `screens` may be `[]` for
   non-UI templates.
5. **Metadata** carries the domain contract: `connections`,
   `frameworks`, `difficulty`, `estimated_time`, plus any
   template-specific block (the dual-brain entry's `bridge` block
   is the pattern for a contract worth naming).

Then verify the catalogue still loads and scaffolds:

```bash
python3 -c "
from eostudio.templates.samples import list_templates, create_project_from_template
print(len(list_templates()))
print(create_project_from_template('<your-key>', '/tmp/check'))
"
```

The repo's test suite loads the catalogue and pins its count —
if you added an entry, the count assertion goes up by one, never
gets deleted.
