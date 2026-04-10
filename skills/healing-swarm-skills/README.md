# healing-swarm-skills

Placeholder for the upstream `github.com/realsammyt/healing-swarm-skills` git submodule.

## Intended Integration

When the upstream repository is available, this directory will be replaced by a git submodule:

```bash
git submodule add https://github.com/realsammyt/healing-swarm-skills.git skills/healing-swarm-skills
```

## How It Works

The `SkillRegistry` in `alchymine/engine/healing/skills/loader.py` supports loading
from multiple directories. Set the `HEALING_SKILLS_EXTERNAL_DIR` environment variable
to point at this directory (or any directory containing YAML skill files):

```env
HEALING_SKILLS_EXTERNAL_DIR=skills/healing-swarm-skills
```

The API will load:
1. Bundled skills from `alchymine/engine/healing/skills/yaml/` (always loaded first)
2. External skills from this directory (merged in, no duplicates allowed)

## Adding Skills

Place YAML files in this directory following the schema defined in
`alchymine/engine/healing/skills/schema.py`. Each file must contain:

- `name` (lowercase-with-dashes slug, must be unique across all directories)
- `modality` (one of the 15 registered modality keys)
- `title`, `description`, `steps`, `evidence_rating`, `duration_minutes`
- Optional: `contraindications`
