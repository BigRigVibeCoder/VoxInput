---
description: Run DarkGravity architect stage to generate a task backlog from a spec
---
// turbo-all

## Steps

1. Resolve the DarkGravity engine location:
```bash
PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
source "$PROJECT_ROOT/bin/resolve_darkgravity.sh" \
  && echo "ENGINE_READY: $DARKGRAVITY_HOME" || echo "ENGINE_MISSING"
```

If `ENGINE_MISSING`, tell the user to run `/darkgravity_setup` first, then stop.

2. Identify the user's architecture request and target project path.

3. Run the architect stage:
```bash
bash "$DARKGRAVITY_HOME/bin/run_pipeline.sh" \
  --request "ARCHITECTURE_REQUEST_HERE" \
  --project "TARGET_PROJECT_PATH" \
  --stages architect \
  --json
```

**Parameter rules:**
- `--request`: The user's design/architecture request (quoted)
- `--project`: Absolute path to the target project directory
- `--stages architect`: Always just `architect` for this workflow
- `--context-files`: Optional, for reference specs or docs (paths relative to project root)
- `--json`: Always include for structured output parsing
- `--config`: Optional, config YAML profile (default: `config/darkgravity.yaml`; use `config/darkgravity_cheap.yaml` for budget runs)
- `--output PATH`: Optional, copy the final output markdown to a specified file path
- `--report [PATH]`: Optional, generate a trace report; pass a path to copy it somewhere specific
- `--quiet`: Optional, suppress the progress UI (useful when piping output)
- `--verbose`: Optional, show DEBUG-level console output
- `--log-level LEVEL`: Optional, set SQLite trace DB level (`TRACE`, `DEBUG`, `INFO`, `WARNING`, `ERROR`)

4. Present the architect's output — typically a structured task backlog
   with phases, file layouts, and implementation details.

5. If `--output` was used, confirm the output file path to the user.

6. Do NOT proceed to coder/tester unless the user explicitly asks.

## Examples

### Basic architecture request
```bash
bash "$DARKGRAVITY_HOME/bin/run_pipeline.sh" \
  --request "Design a plugin system for the renderer" \
  --project /home/user/Documents/my-project \
  --stages architect --json
```

### With context files and output
```bash
bash "$DARKGRAVITY_HOME/bin/run_pipeline.sh" \
  --request "Design the database schema based on the spec" \
  --project /home/user/Documents/my-project \
  --stages architect \
  --context-files CODEX/20_BLUEPRINTS/BLU-001_Spec.md \
  --output /home/user/Documents/my-project/CODEX/20_BLUEPRINTS/BLU-002_DatabaseDesign.md \
  --json
```

## Output Files

The pipeline writes output to `.darkgravity/sessions/` inside the project directory.
Use `--output` to copy the final markdown to a more convenient location.
Use `--report` to generate a trace report showing token usage, model cascades, and timing.

## Troubleshooting

- If `ENGINE_MISSING`: run `/darkgravity_setup` first
- To update the engine path: edit `.agent/darkgravity.conf` with the correct path
- If "ModuleNotFoundError": run `cd "$DARKGRAVITY_HOME" && .venv/bin/pip install -e .`
- If API key errors: check `$DARKGRAVITY_HOME/.env`
