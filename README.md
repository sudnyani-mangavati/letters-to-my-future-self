# Letters to My Future Self

Letters to My Future Self is an **agentic AI system** that allows users to write messages to be delivered to themselves at a future point in time.  
The system is built around **autonomous agents**, **shared persistent memory**, and **event-driven coordination**, rather than a traditional request/response architecture.

This project is intentionally designed as a **real-world applied AI system**, not a demo or chatbot.

---

## Core Concepts

This system explores the following agentic AI patterns:

- Autonomous agents with clear responsibilities
- Shared memory and long-lived state
- Delayed execution and time-based triggers
- Fault tolerance and recoverability
- LLM abstraction and provider flexibility

---

## Run locally

```bash
python -m venv .venv
# Windows:
.\.venv\Scripts\activate

pip install -r requirements.txt
python app.py
```
---

## Architecture Overview

The system is composed of multiple independent agents orchestrated via **LangGraph**:

### Agents
- **CuratorAgent**  
  Parses user input, enriches metadata, and prepares message content for downstream agents.

- **GuardianAgent**  
  Enforces security policies, encrypts sensitive content, and controls access rules.

- **SchedulerAgent**  
  Registers time-based delivery events using a scheduler signal (not as the system brain).

- **MessengerAgent**  
  Handles final message delivery through a pluggable provider interface (email).

Agents communicate through:
- A shared state graph (LangGraph)
- Persistent storage for long-term memory

---

## Data & State Management

- **SQLite** is used for shared memory and message persistence.
- Agent state is strictly validated using **Pydantic schemas**.
- All sensitive message content is encrypted at rest.
- The system is designed to recover cleanly from restarts without losing scheduled messages.

---

## LLM Strategy

- LLM usage is abstracted behind a provider layer.
- Supports:
  - Mock LLM mode (default, no paid keys required)
  - Real providers via configuration
- This enables:
  - Deterministic testing
  - Cost-free local development
  - Easy provider swaps without code changes

---

## Tech Stack

- **Python**
- **LangGraph** — multi-agent orchestration
- **Pydantic** — state and contract validation
- **SQLite** — persistent shared memory
- **APScheduler** — time signal (not orchestration)
- **Cryptography (Fernet)** — encryption at rest

---

## Project Status

**Active development**

Current focus:
- Agent hardening and boundary validation
- Failure handling and retries
- Improving scheduler reliability
- Expanding test coverage

This repository reflects an **iterative, production-style workflow** rather than a one-off build.

---

## Why This Project Exists

Most AI demos stop at prompt engineering.

This project focuses on:
- How agents coordinate over time
- How state persists beyond a single run
- How delayed execution is handled safely
- How AI systems behave outside the happy path

It is intentionally scoped to mirror **real applied AI system design**.
