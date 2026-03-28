---
description: Run the full DarkGravity 4-agent swarm pipeline (Researcher → Architect → Coder → Tester)
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

2. Identify the user's request and target project path. Use the current workspace
   if available, otherwise ask.

3. Run the full 4-stage pipeline:
```bash
bash "$DARKGRAVITY_HOME/bin/run_pipeline.sh" \
  --request "FULL_REQUEST_HERE" \
  --project "TARGET_PROJECT_PATH" \
  --max-fix-attempts 3 \
  --json
```

**Parameter rules (no `--stages` = all 4 run):**
- `--request`: The user's full request (quoted)
- `--project`: Absolute path to the target project directory
- `--context-files`: Optional, for reference docs or specs (paths relative to project root)
- `--max-fix-attempts`: Default 3
- `--json`: Always include for structured output parsing
- Do NOT pass `--stages` — omitting it runs all 4
- `--config`: Optional, config YAML profile (default: `config/darkgravity.yaml`; use `config/darkgravity_cheap.yaml` for budget runs)
- `--web-search`: Optional, enable live web research for the researcher stage (requires `pip install darkgravity[web]`)
- `--output PATH`: Optional, copy the final output markdown to a specified file path
- `--report [PATH]`: Optional, generate a trace report; pass a path to copy it somewhere specific. **Highly recommended for full pipeline runs** to audit token usage and model cascades.
- `--quiet`: Optional, suppress the progress UI (useful when piping output)
- `--verbose`: Optional, show DEBUG-level console output
- `--log-level LEVEL`: Optional, set SQLite trace DB level (`TRACE`, `DEBUG`, `INFO`, `WARNING`, `ERROR`)

4. Parse the JSON result and present:
   - `status` and `elapsed_s`
   - `stages_completed` with individual timing
   - `files_modified` — what the Coder changed
   - `researcher_output` — key findings (summarize if long)
   - `coder_output` — implementation summary
   - `tester_output` — test results
   - `total_cost_usd`
   - Any `errors`

5. If `--output` was used, confirm the output file path to the user.
   If `--report` was used, share the trace report location.

6. Do NOT make additional changes unless the user explicitly asks.

## Important Notes

- Full pipeline takes **5-15 minutes** depending on model availability
- Each stage runs a 4-persona adversarial review (Draftsman → Cynic → Synthesizer → Auditor)
- Coder+Tester run in a fix loop (up to `max_fix_attempts`)
- Cost is typically $0.00-$0.10 using free models with paid fallback

## Examples

### Basic full pipeline
```bash
bash "$DARKGRAVITY_HOME/bin/run_pipeline.sh" \
  --request "Add JWT authentication to the Express API" \
  --project /home/user/Documents/my-express-app \
  --max-fix-attempts 3 --json
```

### Full pipeline with web search, report, and output
```bash
bash "$DARKGRAVITY_HOME/bin/run_pipeline.sh" \
  --request "Implement a caching layer using Redis best practices" \
  --project /home/user/Documents/my-project \
  --web-search \
  --max-fix-attempts 5 \
  --output /home/user/Documents/my-project/CODEX/70_RESEARCH/swarm_output.md \
  --report /home/user/Documents/my-project/CODEX/40_VERIFICATION/ \
  --json
```

### Budget run with cheap config
```bash
bash "$DARKGRAVITY_HOME/bin/run_pipeline.sh" \
  --config config/darkgravity_cheap.yaml \
  --request "Add input validation to all API endpoints" \
  --project /home/user/Documents/my-project \
  --max-fix-attempts 3 --json
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
- If timeout: increase `--max-fix-attempts` or run individual stages
- If `--web-search` fails: run `cd "$DARKGRAVITY_HOME" && .venv/bin/pip install -e ".[web]"`
- To debug issues: add `--verbose --log-level TRACE --report` for full diagnostic capture
