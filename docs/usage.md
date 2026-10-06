# Genesis Hive

A self-evolving multi-agent system that automatically grows specialized AI teams from a single natural-language goal, enables heterogeneous round-table debates among agents, and dynamically restructures the team between debate rounds.

## Core Idea

Most multi-agent systems pre-define a fixed roster of agents. Genesis Hive takes a different approach: given a goal like *"Analyze the feasibility of Xiaohongshu launching AI-powered search"*, it **automatically decomposes** the problem, **spawns** a diverse team of AI agents (each backed by a different LLM, different information sources, and different reasoning frameworks), lets them **debate** in a structured council, and **evolves** the team if knowledge gaps are detected — all without human intervention.

### Why not just prompt one LLM multiple times?

A single LLM role-playing different personas quickly degenerates into an echo chamber. Genesis Hive injects cognitive diversity at three layers:

| Layer | Mechanism | Example |
|---|---|---|
| **Model heterogeneity** | Different agents use different LLM backbones via OpenRouter | GPT-4o-mini (research), Claude Sonnet (analysis), Gemini Flash (devil's advocate) |
| **Information isolation** | Different agents search different source types | Social media vs. academic papers vs. industry reports |
| **Reasoning frameworks** | Each agent's system prompt embeds a distinct analytical lens | JTBD, Gartner Hype Cycle, Unit Economics, Pre-mortem |

## Architecture — Five Evolution Engines

```
Goal (natural language)
  │
  ▼
┌──────────────────┐
│  L1 Decomposer   │  Intent parsing → task graph (3-7 subtasks)
└────────┬─────────┘
         ▼
┌──────────────────┐
│  L2 Spawner      │  Dynamic agent creation (role, prompt, model, tools)
└────────┬─────────┘
         ▼
┌──────────────────┐
│  L3 Executor     │  Async parallel execution with dependency awareness
└────────┬─────────┘
         ▼
┌──────────────────┐
│  L4 Council      │  5-phase debate → consensus detection (judge LLM)
└────────┬─────────┘
         │  ┌─── capability gap? ───┐
         ▼  ▼                       │
┌──────────────────┐                │
│  L5 Evolver      │────────────────┘
│  (dynamic reorg) │  Spawn new agents / retire low-contributors
└────────┬─────────┘
         ▼
┌──────────────────┐
│  Synthesizer     │  Merge conclusions → final report
└──────────────────┘
```

Orchestration is powered by **LangGraph** with `Command` API dynamic routing (no `conditional_edges`). Team restructuring triggers graph recompilation between rounds.

### Council Debate Flow (L4)

The round-table debate engine runs 5 structured phases per round:

| Phase | Name | Description |
|---|---|---|
| A | Present | Each agent publishes preliminary results to the message bus |
| B | Debate | Agents respond with typed messages (challenge / support / rebuttal / supplement / question) |
| C | Revise | Each agent refines conclusions based on debate feedback |
| D | Judge | Independent judge LLM evaluates consensus + contribution scores |
| E | Compress | Lightweight model compresses full debate into a structured summary for next round |

### Executor Resilience (L3)

| Feature | Mechanism |
|---|---|
| Parallel execution | `asyncio.gather()` with dependency-aware `Event` gates |
| Incremental mode | SHA-256 config hash — unchanged agents reuse prior results after evolution |
| Model-level timeout | Per-model timeouts (Claude 30s, Gemini 25s, GPT-4o-mini 20s) |
| Automatic fallback | Timeout → retry with GPT-4o-mini; double-failure → graceful degradation |
| Deadlock prevention | 60s ceiling on dependency waits |

## Tech Stack

| Component | Technologies |
|---|---|
| Backend | Python 3.12+, FastAPI, LangGraph, LangChain Core, AsyncOpenAI |
| Frontend | React 19, TypeScript, Tailwind CSS 4, D3.js 7, Framer Motion 12 |
| LLM Gateway | OpenRouter (unified API for OpenAI / Anthropic / Google models) |
| Real-time | WebSocket (FastAPI native, astream-based event push) |

## Project Structure

```
genesis-hive/
├── backend/
│   ├── engines/                  # Five evolution engines (all production-ready)
│   │   ├── decomposer.py        # L1 — intent parsing → task graph
│   │   ├── spawner.py           # L2 — two-phase concurrent agent generation
│   │   ├── executor.py          # L3 — parallel execution + timeout/fallback
│   │   ├── council.py           # L4 — 5-phase debate (A→E)
│   │   ├── evolver.py           # L5 — low-contribution pruning + gap filling
│   │   └── synthesizer.py       # Final report synthesis
│   ├── core/
│   │   ├── state.py             # HiveState (LangGraph TypedDict, 21 fields)
│   │   ├── llm_service.py       # Multi-model LLM adapter (OpenRouter)
│   │   ├── message_bus.py       # Inter-agent message bus (Pydantic models)
│   │   ├── utils.py             # Shared JSON extraction (extract_json / extract_json_safe)
│   │   ├── consensus.py         # Placeholder (logic in council.py phase_d_judge)
│   │   ├── agent_factory.py     # Placeholder (logic in spawner.py)
│   │   └── tool_pool.py         # Placeholder (mapping in spawner.py)
│   ├── tools/                   # Tool skeletons (web_search, browser, code_executor)
│   ├── api/
│   │   ├── routes.py            # REST API + astream-driven WebSocket events
│   │   └── websocket.py         # WebSocket connection manager
│   ├── graph.py                 # LangGraph orchestration (Command API routing)
│   └── main.py                  # FastAPI entry (CORS, router mount)
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── CouncilRoom.tsx   # Round-table debate (circular layout + chat stream)
│       │   ├── GrowthAnimation.tsx  # Agent spawn animation (D3 force + framer-motion)
│       │   ├── ExecutionBoard.tsx   # Parallel execution dashboard
│       │   ├── EvolutionView.tsx    # Team evolution timeline + metrics
│       │   ├── TeamTopology.tsx     # D3 force-directed team topology graph
│       │   └── FinalReport.tsx      # Final report with confidence ring
│       ├── mockData.ts           # TypeScript interfaces + static demo data
│       └── App.tsx               # Phase selector + component routing
├── test_demo_e2e.py             # Full pipeline demo test (< 2 min)
├── test_graph.py                # LangGraph 3-path routing test
├── test_council_e2e.py          # L1→L4 end-to-end test
├── test_evolver.py              # L5 integration test
├── test_executor_mock.py        # L3 concurrency test (no API key needed)
├── test_executor_e2e.py         # L3 real LLM test
├── test_spawner.py              # L1+L2 end-to-end test
├── test_decomposer.py           # L1 standalone test
├── SKILL.md                     # Full development specification + risk registry
└── README.md
```

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 20+
- An [OpenRouter](https://openrouter.ai/) API key

### 1. Clone and configure

```bash
git clone https://github.com/luxiaoyu0731/genesis-hive.git
cd genesis-hive
cp .env.example .env
# Edit .env and fill in your OPENROUTER_API_KEY
```

### 2. Backend setup

```bash
pip install -r backend/requirements.txt
```

### 3. Frontend setup

```bash
cd frontend && npm install && cd ..
```

### 4. Start the servers

```bash
# Terminal 1 — Backend
uvicorn backend.main:app --reload --port 8000

# Terminal 2 — Frontend
cd frontend && npm run dev
```

The frontend opens at `http://localhost:5173`, backend API docs at `http://localhost:8000/docs`.

### 5. Run via API

```bash
# Start an analysis
curl -X POST http://localhost:8000/api/run \
  -H "Content-Type: application/json" \
  -d '{"goal": "分析小红书做AI搜索的可行性", "mode": "demo"}'

# Check status
curl http://localhost:8000/api/status

# Get full report
curl http://localhost:8000/api/report
```

### 6. Run via Python (CLI)

```python
import asyncio
from backend.graph import build_hive_graph, create_initial_state

async def main():
    state = create_initial_state("分析小红书做AI搜索的可行性", mode="demo")
    graph = build_hive_graph()
    result = await graph.ainvoke(state)
    print(result["final_report"]["executive_summary"])

asyncio.run(main())
```

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `OPENROUTER_API_KEY` | Your OpenRouter API key | *(required)* |
| `OPENROUTER_BASE_URL` | OpenRouter endpoint | `https://openrouter.ai/api/v1` |
| `MODEL_RESEARCH` | Research agents (fast) | `openai/gpt-4o-mini` |
| `MODEL_ANALYSIS` | Analysis agents (deep reasoning) | `anthropic/claude-sonnet-4` |
| `MODEL_ADVERSARY` | Devil's advocate (cognitive diversity) | `google/gemini-2.0-flash-001` |
| `MODEL_META` | Meta-decision (Decomposer/Spawner/Evolver) | `anthropic/claude-sonnet-4` |
| `MODEL_JUDGE` | Independent consensus judge | `openai/gpt-4o` |
| `MODEL_COMPRESS` | Debate summarization (lightweight) | `openai/gpt-4o-mini` |
| `DEFAULT_MODE` | Run mode | `demo` |
| `TOKEN_BUDGET_DEMO` | Demo mode budget | `30000` |
| `TOKEN_BUDGET_STANDARD` | Standard mode budget | `100000` |
| `TOKEN_BUDGET_DEEP` | Deep mode budget | `250000` |

## Run Modes

| Mode | Agents | Debate Rounds | Token Budget | Target Time |
|---|---|---|---|---|
| `demo` | 3 | 1 | 30k | < 2 min |
| `standard` | up to 7 | up to 3 | 100k | ~5 min |
| `deep` | up to 10 | up to 3 + evolution | 250k | ~10 min |

## API Reference

### REST Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Health check |
| `/api/run` | POST | Start analysis (`{"goal": "...", "mode": "demo"}`) |
| `/api/status` | GET | Current run status (idle / running / completed / error) |
| `/api/report` | GET | Full report + debate history + evolution log |
| `/docs` | GET | Interactive Swagger UI |

### WebSocket Events (`/ws`)

Connect via WebSocket to receive real-time events as the pipeline executes:

| Event | Payload | Emitted When |
|---|---|---|
| `run_started` | `{goal, mode}` | Pipeline begins |
| `decomposed` | `{subtask_count, subtasks[]}` | L1 completes task graph |
| `agent_spawned` | `{agent_id, role, model, framework}` | L2 creates each agent |
| `agent_completed` | `{agent_id, confidence, time_ms, tokens_used}` | L3 agent finishes |
| `debate_round_completed` | `{round, consensus_reached, consensus_type}` | L4 round ends |
| `evolution_triggered` | `{cycle, added[], removed[]}` | L5 restructures team |
| `report_ready` | `{title, conclusion, confidence}` | Synthesizer outputs report |
| `run_completed` | `{token_used, debate_rounds}` | Pipeline finishes |
| `run_error` | `{error, trace}` | Pipeline fails |

## Key Design Decisions

- **OpenRouter gateway**: All LLM calls go through OpenRouter for unified billing, rate limiting, and easy model swapping. No direct calls to OpenAI/Anthropic/Google endpoints.
- **Judge LLM for consensus** (not cosine similarity): A dedicated judge model structurally extracts each agent's conclusions and determines whether they agree on substance, not just topic.
- **Debate history compression**: After each round, GPT-4o-mini compresses the full debate into a structured summary (~91% compression ratio). Only the summary enters the next round's context; the full transcript is preserved for the final report.
- **Incremental execution**: When the team evolves, only new/changed agents re-execute. Unchanged agents reuse prior results (verified via SHA-256 `agent_configs_hash`).
- **Two-phase Spawner concurrency**: Regular agents spawn in parallel (Phase 1), then devil's advocate spawns with full team context (Phase 2).
- **Executor timeout + fallback**: Per-model timeout thresholds with automatic fallback to GPT-4o-mini on timeout, plus 60s deadlock prevention on dependency waits.
- **LangGraph Command API**: All routing decisions (council -> synthesizer/evolver/council) use `Command` with `goto`, never `conditional_edges`.

## Tests

| Test | Requires API Key | What it validates |
|---|---|---|
| `test_executor_mock.py` | No | Concurrency, dependency gates, incremental execution |
| `test_decomposer.py` | Yes | L1 output format, subtask bounds |
| `test_spawner.py` | Yes | L1+L2, model heterogeneity, framework diversity |
| `test_executor_e2e.py` | Yes | L1+L2+L3 with real LLMs |
| `test_council_e2e.py` | Yes | L1-L4, all 5 debate phases |
| `test_evolver.py` | Yes | L5 gap detection, low-contribution pruning |
| `test_graph.py` | Yes | 3 LangGraph paths (consensus / evolution / forced) |
| `test_demo_e2e.py` | Yes | Full pipeline, timing < 2 min |

```bash
# Run the only test that doesn't need an API key
python -m test_executor_mock

# Run the full demo test (costs ~35k tokens)
python -m test_demo_e2e
```

## Demo Results

Tested with goal: *"分析小红书做AI搜索的可行性"* in demo mode:

| Metric | Value |
|---|---|
| Total time | ~115s |
| Total tokens | ~34k |
| Agents | 3 (market researcher + tech analyst + devil's advocate) |
| Debate rounds | 1 |
| Consensus | Full (all agents: "conditionally feasible") |
| Compression ratio | 91.5% |
| Conclusion | Conditionally feasible (confidence 0.74) |

## License

MIT
