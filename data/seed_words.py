"""
VoxInput Protected Words — Initial Seed Dataset v2

1200+ words across 12 categories.
Optimized for: Linux power user + software developer + AI/ML engineer.
Research sources: NVIDIA Riva ASR wordlists, Speechmatics custom dict guides,
                  AI/ML glossaries (2024-2025), GitHub developer surveys.

Run to seed:
    python3 -m data.seed_words
"""

# fmt: off
SEED_WORDS: list[tuple[str, str]] = [

    # ── Tech abbreviations & shell terms ────────────────────────────────────
    *[(w, "tech") for w in [
        # Protocols / formats
        "api", "url", "uri", "http", "https", "html", "css", "json", "xml",
        "yaml", "toml", "csv", "sql", "nosql", "orm", "sdk", "ide", "cli",
        "gui", "tui", "os", "ui", "ux", "vm", "venv", "env", "ssh", "ftp",
        "sftp", "vpn", "dns", "ip", "tcp", "udp", "lan", "wan", "nat",
        "cpu", "gpu", "ram", "ssd", "hdd", "nvme", "usb", "hdmi", "dp",
        "bios", "uefi", "io", "db", "oop", "fp", "dsl",
        # AI / ML abbreviations
        "ml", "ai", "dl", "llm", "nlp", "ocr", "tts", "asr", "rag",
        "rl", "rlhf", "ppo", "dpo", "sft", "gpt", "bert", "vae", "gan",
        "cnn", "rnn", "lstm", "gru", "mlp", "moe", "kv", "knn",
        "slm", "vlm", "vllm", "llama", "mamba", "ssm", "rwkv",
        # DevOps / infra
        "ci", "cd", "pr", "mr", "repo", "dev", "devops", "sre", "soc",
        "poc", "mvp", "kpi", "roi", "saas", "paas", "iaas", "caaS",
        "rpc", "grpc", "rest", "graphql", "oauth", "jwt", "cors", "csrf",
        "xss", "tls", "ssl", "mtls", "rbac", "iam",
        # Languages (spoken as abbreviations)
        "py", "js", "ts", "rs", "go", "cpp", "tsx", "jsx", "wasm",
        # File formats
        "pdf", "png", "jpg", "jpeg", "svg", "gif", "webp",
        "mp3", "mp4", "mkv", "wav", "flac", "ogg",
        "tar", "zip", "gzip", "bzip", "xz", "deb", "rpm", "appimage",
        # Shell / Linux
        "regex", "stdin", "stdout", "stderr", "sudo", "chmod", "chown",
        "grep", "awk", "sed", "bash", "zsh", "fish", "cron", "crontab",
        "pid", "uid", "gid", "inode", "symlink", "hardlink",
        "mutex", "semaphore", "futex", "mmap", "syscall",
        "async", "await", "bool", "int", "str", "dict", "list",
        "tuple", "enum", "null", "nan", "inf", "utf", "ascii",
        # Networking
        "ipv4", "ipv6", "cidr", "bgp", "ospf", "vlan", "dhcp",
        "smtp", "imap", "pop3", "websocket", "mqtt", "coap",
        # Security
        "csrf", "xss", "sqli", "rce", "lfi", "ssrf", "idor",
        "pentest", "ctf", "opsec", "2fa", "mfa", "otp", "totp",
    ]],

    # ── Linux kernel & system internals ─────────────────────────────────────
    *[(w, "linux") for w in [
        # Distros
        "linux", "ubuntu", "debian", "fedora", "centos", "arch", "mint",
        "kali", "nixos", "alpine", "gentoo", "slackware", "opensuse",
        "void", "artix", "manjaro", "endeavouros", "popos", "elementary",
        "zorin", "tails", "whonix", "qubes", "raspbian", "dietpi",
        # Desktop environments & compositors
        "gnome", "kde", "xfce", "lxqt", "i3", "sway", "hyprland",
        "wayland", "xorg", "x11", "wlroots", "pipewire", "pulseaudio", "alsa",
        "openbox", "bspwm", "dwm", "awesome", "qtile",
        # System components
        "systemd", "openrc", "runit", "dinit", "s6",
        "udev", "dbus", "polkit", "cgroups", "namespaces", "seccomp",
        "selinux", "apparmor", "lsm", "landlock",
        "initramfs", "grub", "efi", "luks", "lvm", "btrfs", "zfs",
        "ext4", "xfs", "tmpfs", "overlayfs",
        "nftables", "iptables", "ebpf", "bpf", "xdp",
        # Package managers & formats
        "apt", "dpkg", "rpm", "dnf", "yum", "pacman", "aur", "flatpak",
        "snap", "appimage", "nix", "guix", "homebrew",
        # Kernel / hardware
        "kernel", "kvm", "qemu", "libvirt", "vfio", "passthrough",
        "dkms", "modprobe", "insmod", "rmmod", "lsmod",
        "dmesg", "journalctl", "sysctl", "strace", "ltrace", "perf",
        "valgrind", "gdb", "lldb", "coredump",
        # Terminals & multiplexers
        "tmux", "zellij", "screen", "kitty", "alacritty", "wezterm",
        "konsole", "terminator", "tilix",
        # Tools
        "vim", "neovim", "emacs", "helix", "kakoune",
        "git", "gh", "lazygit", "tig",
        "fzf", "ripgrep", "fd", "bat", "eza", "lsd", "zoxide", "atuin",
        "htop", "btop", "glances", "netstat", "ss", "lsof", "iostat",
        "curl", "wget", "httpie", "xh", "netcat", "socat",
        "rsync", "rclone", "restic", "borgbackup",
        "ansible", "terraform", "pulumi", "nix", "guix",
    ]],

    # ── Programming languages & ecosystems ──────────────────────────────────
    *[(w, "dev") for w in [
        # Languages
        "python", "javascript", "typescript", "kotlin", "golang", "haskell",
        "erlang", "elixir", "clojure", "scala", "swift", "rust", "julia",
        "matlab", "fortran", "cobol", "assembly", "webassembly",
        "solidity", "move", "vyper",  # web3
        "gleam", "roc", "zig", "nim", "crystal", "odin", "vale",  # emerging
        # Python ecosystem
        "numpy", "pandas", "polars", "scipy", "matplotlib", "seaborn",
        "plotly", "streamlit", "gradio", "fastapi", "django", "flask",
        "starlette", "litestar", "pydantic",
        "celery", "dramatiq", "rq", "prefect", "airflow", "dagster",
        "sqlalchemy", "alembic", "tortoise", "piccolo",
        "pytest", "hypothesis", "locust", "faker",
        "pyproject", "hatch", "rye", "uv", "poetry",  # modern packaging
        # JS/TS ecosystem
        "react", "angular", "svelte", "solidjs", "qwik", "astro",
        "nextjs", "nuxtjs", "remix", "sveltekit", "tanstack",
        "vite", "esbuild", "turbopack", "webpack", "rollup", "parcel",
        "bun", "deno", "node", "nodejs",
        "vitest", "playwright", "cypress", "puppeteer",
        "prisma", "drizzle", "sequelize",
        # Rust ecosystem
        "tokio", "actix", "axum", "tide", "warp",
        "serde", "rayon", "crossbeam", "dashmap",
        "rustup", "cargo", "clippy",
        # DevOps & infra
        "docker", "kubernetes", "helm", "kustomize", "skaffold",
        "ansible", "terraform", "pulumi", "cdk", "serverless",
        "nginx", "caddy", "traefik", "envoy", "istio", "linkerd",
        "prometheus", "grafana", "loki", "tempo", "jaeger", "opentelemetry",
        "datadog", "newrelic", "sentry",
        # Databases
        "postgres", "postgresql", "mysql", "mariadb", "sqlite",
        "mongodb", "redis", "valkey", "dragonfly", "cassandra",
        "elasticsearch", "opensearch", "meilisearch", "typesense",
        "kafka", "pulsar", "nats", "rabbitmq", "zmq", "zeromq",
        "clickhouse", "duckdb", "motherduck", "turso", "tidb",
        "qdrant", "weaviate", "milvus", "chroma", "pinecone",  # vector DBs
        # Git & collaboration
        "github", "gitlab", "bitbucket", "gitea", "forgejo",
        "jira", "linear", "notion", "confluence", "coda",
        # IDEs
        "vscode", "cursor", "zed", "neovim", "jetbrains",
        "pycharm", "intellij", "webstorm", "goland", "clion",
        "windsurf", "trae",  # new AI-native editors
    ]],

    # ── AI, ML, LLM — cutting edge ──────────────────────────────────────────
    *[(w, "ai") for w in [
        # Frameworks & libraries
        "pytorch", "tensorflow", "jax", "flax", "haiku",
        "keras", "sklearn", "scikit", "lightgbm", "xgboost", "catboost",
        "huggingface", "transformers", "datasets", "tokenizers", "accelerate",
        "peft", "trl", "bitsandbytes", "unsloth", "axolotl",
        "langchain", "llamaindex", "haystack", "dspy", "guidance",
        "ollama", "vllm", "tgi", "lmdeploy",  # inference
        "triton", "trt", "tensorrt", "onnx", "onnxruntime",
        "diffusers", "comfyui", "a1111", "invokeai", "fooocus",
        # Models & families
        "gpt", "chatgpt", "openai", "gemini", "claude", "anthropic",
        "llama", "mistral", "mixtral", "phi", "gemma", "qwen",
        "deepseek", "yi", "cohere", "command", "titan",
        "whisper", "bark", "elevenlabs", "xtts", "coqui",
        "stable diffusion", "sdxl", "flux", "imagen", "dalle",
        "sora", "runway", "pika", "kling", "wan",  # video gen
        "midjourney", "firefly", "leonardo",  # image gen
        # Concepts
        "transformer", "attention", "multihead", "embeddings", "tokenizer",
        "tokenization", "pretraining", "finetuning", "rlhf", "rlaif",
        "dpo", "ppo", "grpo", "orpo", "sft", "lora", "qlora", "dora",
        "gguf", "ggml", "exl2", "awq", "gptq",  # quantization formats
        "quantization", "pruning", "distillation", "speculative",
        "moe", "ssm", "mamba", "rwkv", "hyena",  # architectures
        "rag", "agentic", "multiagent", "tooluse", "functioncalling",
        "chainofthought", "treethought", "selfconsistency",
        "hallucination", "grounding", "alignment", "guardrails",
        "promptengineering", "fewshot", "zeroshot", "oneshot",
        "vectordb", "embeddings", "chunking", "reranking", "rerankr",
        "langsmith", "wandb", "mlflow", "bentoml", "modal",
        "cursor", "copilot", "codeium", "tabnine", "supermaven",
        "devin", "swebench", "aider", "mentat",
        # Hardware
        "cuda", "cudnn", "triton", "rocm", "opencl", "vulkan", "metal",
        "h100", "a100", "v100", "tpu", "gaudi", "groq", "trainium",
    ]],

    # ── Cloud & infrastructure ───────────────────────────────────────────────
    *[(w, "cloud") for w in [
        "aws", "gcp", "azure", "cloudflare", "vercel", "netlify",
        "fly", "railway", "render", "heroku", "digitalocean", "linode",
        "vultr", "hetzner", "ovh", "backblaze",
        "ec2", "s3", "rds", "eks", "ecs", "ecs", "lambda", "sqs",
        "sns", "cloudwatch", "cloudfront", "route53", "vpc", "iam",
        "gke", "gcs", "bigquery", "pubsub", "cloudbuild",
        "aks", "blob", "cosmos", "eventhub", "servicebus",
        "terraform", "opentofu", "pulumi", "cdk",
        "argocd", "fluxcd", "tekton", "circleci", "github actions",
        "buildkite", "drone",
    ]],

    # ── Organizations, agencies, consortia ──────────────────────────────────
    *[(w, "org") for w in [
        # Government / Military
        "nasa", "fbi", "cia", "nsa", "dea", "atf", "irs", "fda", "epa",
        "doj", "dod", "dhs", "cbp", "tsa", "sec", "ftc", "fcc",
        "usaf", "usmc", "usn", "uscg", "nato", "cia", "fema",
        "cdc", "nih", "hhs", "nist", "darpa", "arpa",
        # Tech consortia / standards
        "ietf", "ieee", "w3c", "osi", "iso", "ansi", "posix",
        "openai", "deepmind", "googledeepmind", "xai",
        "mlcommons", "lfai", "lf", "cncf", "opencontainers",
        "apache", "gnu", "fsf", "osi", "linuxfoundation",
        # Sports
        "nfl", "nba", "mlb", "nhl", "nascar", "ufc", "wwe", "pga",
        "ncaa", "espn", "usoc", "fifa", "uefa",
        # Finance / biz
        "fednow", "fdic", "cftc", "occ", "bis",
        "blackrock", "vanguard", "jpmorgan", "goldman", "berkshire",
        # Media
        "amc", "hbo", "cnn", "fox", "nbc", "abc", "cbs", "pbs",
        "npr", "bbc", "ap", "reuters", "bloomberg",
    ]],

    # ── Brands & companies ───────────────────────────────────────────────────
    *[(w, "brand") for w in [
        # Big tech
        "google", "apple", "microsoft", "amazon", "meta", "netflix",
        "twitter", "instagram", "facebook", "whatsapp", "telegram",
        "spotify", "youtube", "reddit", "discord", "slack", "zoom",
        "dropbox", "stripe", "twilio", "sendgrid", "cloudflare",
        "ibm", "oracle", "sap", "salesforce", "adobe", "autodesk",
        "qualcomm", "amd", "intel", "arm", "broadcom",
        "tesla", "spacex", "palantir", "snowflake", "databricks",
        "anyscale", "together", "replicate", "perplexity", "mistral",
        # Consumer
        "nike", "adidas", "carhartt", "timberland",
        "ford", "chevy", "chevrolet", "dodge", "jeep", "gmc",
        "toyota", "honda", "subaru", "harley",
        "walmart", "costco", "target", "lowes", "homedepot",
        "starbucks", "dunkin", "mcdonald's",
        "verizon", "at&t", "tmobile", "comcast",
    ]],

    # ── US places ────────────────────────────────────────────────────────────
    *[(w, "place") for w in [
        "alabama", "alaska", "arizona", "arkansas", "california",
        "colorado", "connecticut", "delaware", "florida", "georgia",
        "hawaii", "idaho", "illinois", "indiana", "iowa", "kansas",
        "kentucky", "louisiana", "maine", "maryland", "massachusetts",
        "michigan", "minnesota", "mississippi", "missouri", "montana",
        "nebraska", "nevada", "ohio", "oklahoma", "oregon",
        "pennsylvania", "tennessee", "texas", "utah", "vermont",
        "virginia", "washington", "wisconsin", "wyoming",
        "chicago", "houston", "phoenix", "philadelphia", "dallas",
        "seattle", "denver", "boston", "atlanta", "miami", "portland",
        "minneapolis", "detroit", "baltimore", "nashville", "raleigh",
        "pittsburgh", "cincinnati", "tampa", "orlando",
        "manhattan", "brooklyn", "bronx", "queens", "harlem",
        "silicon valley", "austin", "reston", "redmond", "cupertino",
        "menlo park", "mountain view",
    ]],

    # ── American first names ─────────────────────────────────────────────────
    *[(w, "name") for w in [
        # Male
        "james", "john", "robert", "michael", "william", "david", "richard",
        "joseph", "thomas", "charles", "christopher", "daniel", "matthew",
        "anthony", "mark", "donald", "steven", "paul", "andrew", "kenneth",
        "joshua", "kevin", "brian", "george", "timothy", "ronald", "edward",
        "jason", "jeffrey", "ryan", "jacob", "gary", "nicholas", "eric",
        "jonathan", "stephen", "larry", "justin", "scott", "brandon",
        "benjamin", "samuel", "raymond", "gregory", "frank", "alexander",
        "patrick", "jack", "dennis", "jerry", "tyler", "henry",
        "doug", "dave", "mike", "chris", "bob", "bill", "joe", "jim",
        "tom", "rick", "dan", "steve", "jeff", "pete", "matt", "andy",
        "brad", "brett", "chad", "chuck", "clint", "cole", "cody",
        "derek", "drew", "dylan", "ethan", "evan", "troy", "travis",
        "trevor", "zach",
        # Female
        "mary", "patricia", "jennifer", "linda", "barbara", "susan",
        "jessica", "sarah", "karen", "lisa", "nancy", "betty",
        "sandra", "ashley", "emily", "donna", "michelle", "carol", "amanda",
        "melissa", "deborah", "stephanie", "rebecca", "laura", "amy",
        "angela", "anna", "brenda", "pamela", "emma", "nicole",
        "samantha", "katherine", "christine", "rachel", "carolyn", "maria",
        "heather", "diane", "julie", "victoria", "kelly", "kim", "kate", "tara",
    ]],

    # ── American sports ──────────────────────────────────────────────────────
    *[(w, "sports") for w in [
        # NFL teams
        "patriots", "cowboys", "packers", "steelers", "raiders", "chiefs",
        "broncos", "seahawks", "eagles", "ravens", "bengals", "browns",
        "texans", "jaguars", "titans", "colts", "bills", "dolphins",
        "jets", "chargers", "rams", "niners", "cardinals", "falcons",
        "panthers", "saints", "buccaneers", "vikings", "bears", "lions",
        "giants", "commanders",
        # NBA teams
        "lakers", "celtics", "warriors", "bulls", "heat", "spurs",
        "knicks", "nets", "mavericks", "suns", "nuggets", "clippers",
        "bucks", "sixers", "raptors", "hawks", "jazz", "thunder",
        # MLB teams
        "yankees", "redsox", "dodgers", "cubs", "braves", "astros",
        "mets", "phillies", "padres", "brewers", "rangers",
        # Sports terms
        "quarterback", "touchdown", "interception", "superbowl",
        "fastball", "strikeout", "homerun", "layup", "alleyoop",
        "nascar", "indy", "motocross",
    ]],

    # ── Culture / media / entertainment ─────────────────────────────────────
    *[(w, "culture") for w in [
        "netflix", "hulu", "hbo", "espn", "disney", "peacock", "paramount",
        "marvel", "avengers", "batman", "superman", "spiderman",
        "starwars", "jedi", "sith", "mandalorian",
        "country", "bluegrass", "jazz", "blues", "metalcore",
        "playstation", "xbox", "nintendo", "fortnite", "minecraft",
        "valorant", "overwatch", "warzone", "callofduty", "halo",
        "madden", "nba2k", "gta", "skyrim", "fallout", "zelda",
        "twitch", "steam",
        "barbecue", "brisket", "ribs", "tailgate",
    ]],

    # ── VoxInput / HiveMind project & user-specific ──────────────────────────
    *[(w, "project") for w in [
        "voxinput", "hivemind", "bigrig", "antigravity", "phantom",
        "cortex", "arbiter", "reflex", "sensorium", "pathfinder",
        "atlas", "fogofwar", "neuralbreach", "gladiator",
        "symspell", "pyaudio", "pulseaudio", "ydotool", "xdotool",
        "gtk", "glib", "gobject", "cairo", "pango", "wayland",
        "zeromq", "pydantic", "fastapi", "uvicorn", "ctypes",
        "bigrigvibecoder", "forgerunner",
    ]],

    # ── Futurist / emerging tech ─────────────────────────────────────────────
    *[(w, "future") for w in [
        # AI agents & agentic frameworks
        "agentic", "multiagent", "openagents", "autogpt", "babyagi",
        "crewai", "autogen", "agentops", "langgraph", "smolagents",
        # AI safety & alignment
        "alignment", "interpretability", "mechanistic", "superalignment",
        "constitutionalai", "rlaif", "dpo", "orpo",
        # Robotics
        "openpi", "pi0", "lerobot", "diffusionpolicy", "act",
        "ros", "ros2", "gazebo", "isaac",
        # Web3 / crypto (spoken about)
        "blockchain", "ethereum", "bitcoin", "solana", "polygon",
        "defi", "nft", "dao", "zkproof", "zkrollup", "eigenlayer",
        # Hardware trends
        "neuromorphic", "photonic", "memristor", "risc-v", "riscv",
        # Edge / IoT
        "edgeai", "tinyml", "onnx", "coreml", "tflite",
        "esp32", "raspberry pi", "arduino", "jetson",
        # Spatial computing
        "visionpro", "xr", "ar", "vr", "metaverse", "digitaltwins",
        # Quantum
        "qubits", "superposition", "entanglement", "qiskit", "cirq",
    ]],

    # ── Agile, Scrum & agentic software dev workflow ─────────────────────────
    *[(w, "agile") for w in [
        # Agile / Scrum ceremonies & artifacts
        "scrum", "kanban", "sprint", "backlog", "standup", "retrospective",
        "refinement", "grooming", "velocity", "burndown", "burnup",
        "epics", "stories", "userstory", "acceptance criteria", "dod",
        "dor", "wip", "timebox", "pomodoro", "scrummaster", "productowner",
        "stakeholder", "blocker", "impediment", "taskboard", "swimlane",
        # Engineering practices
        "tdd", "bdd", "ddd", "atdd",
        "refactor", "refactoring", "codebase", "codeowner", "linter",
        "formatter", "precommit", "commitizen", "conventional commits",
        "trunk", "gitflow", "rebase", "squash", "cherrypick", "stash",
        "ci", "cd", "pipeline", "workflow", "action", "webhook",
        "codecoverage", "codeclimate", "sonarqube", "codecov",
        "unittest", "integration test", "e2e", "endtoend", "fixture",
        "mock", "stub", "spy", "faker", "factory", "parametrize",
        "decorator", "metaclass", "mixin", "mro", "dunder",
        "generator", "coroutine", "asyncio", "threadpool", "multiprocessing",
        "subprocess", "contextmanager", "dataclass", "namedtuple",
        "typevar", "protocol", "runtime", "interpreter", "bytecode",
        # Agentic dev concepts
        "agentic", "orchestrator", "subagent", "handoff", "toolcall",
        "functioncalling", "tooluse", "planandexecute", "reactagent",
        "cot", "tot", "got", "reflexion", "self-reflection",
        "longcontext", "contextwindow", "memgpt", "memoryagent",
        "retrieval", "chunking", "embedding", "bm25", "hybrid search",
        "rerank", "guardrail", "evaluator", "evals",
        "langsmith", "arize", "phoenix", "trulens", "deepeval",
        # Architecture patterns
        "microservices", "monolith", "hexagonal", "onion", "clean arch",
        "cqrs", "eventsourcing", "saga", "outbox", "sidecar",
        "api gateway", "bff", "servicemesh", "serviceregistry",
        "circuitbreaker", "bulkhead", "ratelimiting", "backpressure",
        "pubsub", "eventdriven", "messagebus", "commandbus",
        "repository pattern", "factory", "singleton", "observer",
        "decorator pattern", "adapter", "facade",
        # Python-specific
        "pyproject", "setuptools", "hatchling", "flit", "maturin",
        "mypy", "pyright", "ruff", "black", "isort", "pylint",
        "bandit", "safety", "semgrep",
        "pep8", "pep517", "pep518", "pep621",
        "virtualenv", "conda", "mamba", "micromamba",
        "asyncpg", "aiohttp", "httpx", "aiofiles",
        "typer", "click", "argparse", "rich", "textual",
        "loguru", "structlog",
    ]],
]
# fmt: on


def seed_database(db_path: str = None):
    """Seed the word database with the initial dataset (no-op if already seeded)."""
    import os
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from src.word_db import WordDatabase

    if db_path is None:
        db_path = os.path.join(os.path.dirname(__file__), "..", "data", "custom_words.db")

    db = WordDatabase(db_path)
    db.seed(SEED_WORDS)
    print(f"Database contains {db.count()} protected words  [{db_path}]")
    db.close()


if __name__ == "__main__":
    seed_database()
