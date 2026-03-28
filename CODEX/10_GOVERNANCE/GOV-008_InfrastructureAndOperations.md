---
id: GOV-008
title: "Infrastructure & Operations Standard"
type: reference
status: APPROVED
owner: architect
agents: [all]
tags: [governance, standards, infrastructure, deployment, operations, linux]
related: [GOV-007, BLU-020]
created: 2026-03-24
updated: 2026-03-28
version: 1.1.0
---

> **BLUF:** This document captures all infrastructure decisions that override or adapt the architecture blueprint for VoxInput. It defines the Linux Desktop runtime, C-Extension build targets, PulseAudio routing, and model limits. This forms the operational reality for all Sprints.

# Infrastructure & Operations Standard

> **"Architecture assumes. Infrastructure decides."**

---

## 1. Deployment Model (Desktop Linux Native)

Unlike standard web blueprints, VoxInput is a persistent background Linux desktop daemon running inside the user's session with strict memory boundaries.

| Decision | Value |
|:---------|:------|
| **Deployment target** | `Local Desktop UNIX Session (User-space)` |
| **OS Support** | `Ubuntu / Debian based (Pop!_OS, etc.)` |
| **Environment** | `PyGObject (GTK3), X11 / XWayland Native` |

### Adaptation Table

> Aligning Web-First Blueprint standards to Desktop Native realities.

| Blueprint Assumption | Actual (GOV-008) |
|:--------------------|:-----------------|
| `[Docker / Cloud Run]` | `[Python venv / .desktop file]` |
| `[PostgreSQL / Cloud SQL]` | `[Local SQLite custom_words.db & JSON config]` |
| `[HTTP REST APIs]` | `[Direct lib_rms.so C-Extension memory passing]` |

---

## 2. Hardware Abstraction & Audio Routing

| Decision | Value |
|:---------|:------|
| **Audio Server** | `PulseAudio / ALSA via PyAudio` |
| **Microphone Lock** | `Exclusive/Shared access based on host config` |
| **Keyboard Injection** | `xdotool (primary) -> ydotool (Wayland) -> pynput (Unicode fallback)` |

---

## 3. Repository Structure & Bootstrapping

| Decision | Value |
|:---------|:------|
| **Structure** | `Monorepo with bundled CODEX Project Management` |
| **Bootstrapper** | `bash install.sh (Automates APT & venv)` |

---

## 4. Performance & Memory Profile (The C Extension)

A single offline model (Vosk/Whisper) easily saturates 5.4GB RAM. Audio ingestion must be ultra-lean.

| Decision | Value |
|:---------|:------|
| **Ingestion Gate** | `RMS evaluated per-chunk via native C extension` |
| **C Extension Source** | `src/c_ext/rms.c` |
| **Fallback** | `Numpy wrapper on Python 3.10+` |

---

## 5. File Storage & Configuration

| Decision | Value |
|:---------|:------|
| **Storage model** | `Local disk (~/Documents/VoxInput)` |
| **Config path** | `settings.json` |

---

## 6. Monitoring & Observability

| Decision | Value |
|:---------|:------|
| **Error tracking** | `Local structlog rotation (voxinput.log)` |
| **Log aggregation** | `SQLite / local file system` |
| **Crash dumps** | `sys.excepthook overriding` |
