---
description: Run DarkGravity coder+tester stages to generate and test code
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

2. Identify the user's coding request and target project path.

3. Run the coder+tester stages:
```bash
bash "$DARKGRAVITY_HOME/bin/run_pipeline.sh" \
  --request "CODING_REQUEST_HERE" \
  --project "TARGET_PROJECT_PATH" \
  --stages coder tester \
  --max-fix-attempts 3 \
  --json
```

**Parameter rules:**
- `--request`: The user's coding request (quoted)
- `--project`: Absolute path to the target project directory
- `--stages coder tester`: Always both together (they run in a fix loop)
- `--max-fix-attempts`: Default 3, increase for complex tasks
- `--context-files`: Optional, for specs or reference code (paths relative to project root)
- `--json`: Always include for structured output parsing
- `--config`: Optional, config YAML profile (default: `config/darkgravity.yaml`; use `config/darkgravity_cheap.yaml` for budget runs)
- `--output PATH`: Optional, copy the final output markdown to a specified file path
- `--report [PATH]`: Optional, generate a trace report; pass a path to copy it somewhere specific
- `--quiet`: Optional, suppress the progress UI (useful when piping output)
- `--verbose`: Optional, show DEBUG-level console output (helpful for debugging fix loops)
- `--log-level LEVEL`: Optional, set SQLite trace DB level (`TRACE`, `DEBUG`, `INFO`, `WARNING`, `ERROR`; use `TRACE` to capture full fix-loop detail)

4. Parse the JSON result and present:
   - `files_modified` — what was created/changed
   - `coder_output` — implementation details
   - `tester_output` — test results and pass/fail
   - `elapsed_s` and cost summary

5. If `--output` was used, confirm the output file path to the user.

6. Do NOT proceed to additional stages unless the user explicitly asks.

## Important Notes

- Coder and Tester always run together in a fix loop
- The Coder writes code, the Tester runs tests, failed → Coder revises
- Loops up to `max_fix_attempts` times
- Use `--verbose` or `--log-level TRACE` to debug persistent test failures

## Examples

### Basic coding request
```bash
bash "$DARKGRAVITY_HOME/bin/run_pipeline.sh" \
  --request "Implement the login endpoint from the architect spec" \
  --project /home/user/Documents/my-project \
  --stages coder tester --max-fix-attempts 3 --json
```

### Complex task with verbose debugging and trace report
```bash
bash "$DARKGRAVITY_HOME/bin/run_pipeline.sh" \
  --request "Refactor the data layer to use repository pattern" \
  --project /home/user/Documents/my-project \
  --stages coder tester \
  --max-fix-attempts 5 \
  --context-files CODEX/20_BLUEPRINTS/BLU-003_DataLayerSpec.md \
  --verbose \
  --log-level TRACE \
  --report \
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
- If fix loop exhausted: increase `--max-fix-attempts` or simplify the request
- To debug fix loops: add `--verbose --log-level TRACE` and review the trace report with `--report`
