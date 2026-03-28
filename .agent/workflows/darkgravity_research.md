---
description: Run DarkGravity research swarm on a topic or attached documents
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

2. Identify the user's research topic from their message. Note any referenced documents.

3. If documents were referenced, note their absolute paths. If they're not in the
   project directory, copy them in first.

4. Run the research swarm via the CLI runner:
```bash
bash "$DARKGRAVITY_HOME/bin/run_pipeline.sh" \
  --request "RESEARCH_TOPIC_HERE" \
  --project "TARGET_PROJECT_PATH" \
  --stages researcher \
  --json
```

**Parameter rules:**
- `--request`: The user's research topic (natural language, quoted)
- `--project`: Absolute path to the target project directory
- `--stages researcher`: Always just `researcher` for this workflow
- `--context-files`: Optional, relative paths from project root for reference docs
- `--json`: Always include for structured output parsing
- `--config`: Optional, config YAML profile (default: `config/darkgravity.yaml`; use `config/darkgravity_cheap.yaml` for budget runs)
- `--web-search`: Optional, enable live web research (requires `pip install darkgravity[web]`)
- `--output PATH`: Optional, copy the final output markdown to a specified file path
- `--report [PATH]`: Optional, generate a trace report; pass a path to copy it somewhere specific
- `--quiet`: Optional, suppress the progress UI (useful when piping output)
- `--verbose`: Optional, show DEBUG-level console output
- `--log-level LEVEL`: Optional, set SQLite trace DB level (`TRACE`, `DEBUG`, `INFO`, `WARNING`, `ERROR`)

5. Parse the JSON result and present `researcher_output` in a well-formatted manner.
   Include `elapsed_s` and token counts as a summary footer.

6. If `--output` was used, confirm the output file path to the user.

7. Do NOT proceed to additional stages unless the user explicitly asks.

## Examples

### Basic research
```bash
bash "$DARKGRAVITY_HOME/bin/run_pipeline.sh" \
  --request "Research quantum error correction breakthroughs in 2026" \
  --project /home/user/Documents/my-project \
  --stages researcher --json
```

### Research with web search and output file
```bash
bash "$DARKGRAVITY_HOME/bin/run_pipeline.sh" \
  --request "Research latest vLLM performance benchmarks" \
  --project /home/user/Documents/my-project \
  --stages researcher \
  --web-search \
  --output /home/user/Documents/my-project/CODEX/70_RESEARCH/RES-001_vLLM_Benchmarks.md \
  --report \
  --json
```

### Budget research with cheap config
```bash
bash "$DARKGRAVITY_HOME/bin/run_pipeline.sh" \
  --config config/darkgravity_cheap.yaml \
  --request "Survey edge deployment frameworks" \
  --project /home/user/Documents/my-project \
  --stages researcher --json
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
- If `--web-search` fails: run `cd "$DARKGRAVITY_HOME" && .venv/bin/pip install -e ".[web]"`
