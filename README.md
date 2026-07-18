# Academic Job Sourcing & Refinement

Automated academic job sourcing, metadata refinement, and CV matching pipeline. Uses local, CPU-optimized models (Gemma-4, SentenceTransformers, and NLLB-200) to translate, detect languages, extract structured skills, prerequisite degrees, and match candidates against positions.

---

## 1. Project Structure

```text
├── packages/
│   ├── core/                          # Shared domain models, DB repositories, and SDK utilities
│   │   └── src/core/utils/agent.py    # Standardized signal-aware agent loop utility
│   ├── api/                           # FastAPI gateway server and database coordinator
│   └── agents/                        # Isolated worker packages running in parallel
│       ├── euraxess-discovery/            # EURAXESS search pagination discovery agent
│       ├── euraxess-sourcing/             # EURAXESS page details fetcher agent
│       ├── academictransfer-discovery/    # AcademicTransfer search pagination discovery agent
│       ├── academictransfer-sourcing/     # AcademicTransfer page details fetcher agent
│       ├── lang-detection/                # Standalone local language detection agent
│       ├── translation/                   # Standalone local NLLB-200 translation agent
│       ├── refinement/                    # Local Gemma-4 metadata extractor & refiner agent
│       └── matching/                      # Candidate CV matching & LLM explanation agent
├── pyproject.toml                     # Root workspace configuration
├── uv.lock                           # Workspace dependency lockfile
├── .env.example                       # Settings template file
├── Dockerfile                         # Unified multi-purpose Dockerfile
└── docker-compose.yml                 # Unified Docker Compose orchestration config
```

---

## 2. Requirements

*   **Docker & Docker Compose** (highly recommended for unified execution)
*   **Python**: `>= 3.12` (if running locally without containers)
*   **Environment Manager**: [uv](https://github.com/astral-sh/uv) (for local CLI runs)
*   **Hardware requirements**:
    *   **Refinement Agent**: ~2.8GB RAM to load the `gemma-4-E2B-it-Q4_K_M` GGUF model via llama-cpp-python (idle RAM drops to ~40MB with auto-unload).
    *   **Translation Agent**: ~600MB RAM to load the quantized `NLLB-200-distilled-600M` model.
    *   **Matching Agent**: Loads the `Gemma-4` GGUF explainer model on demand and uses `nomic-embed-text-v1.5` for candidate matching.
*   **Database**: SQLite (default local file `jobs.db` mounted in containers) or PostgreSQL.

---

## 3. Quick Start with Docker Compose (Recommended)

Running the entire stack (API server + crawlers + NLP workers) takes a single command:

### A. Configure Environment
Create your local `.env` file from the template:
```bash
cp .env.example .env
```
Edit `.env` to verify your variables.

### B. Boot the Stack
Build and launch all containers in the background:
```bash
docker compose up --build -d
```
Docker Compose will automatically:
1. Boot the **FastAPI gateway (`api`)** and run database schema initializations.
2. Run automated health checks until the API is healthy.
3. Start the background **scrapers** (Euraxess and AcademicTransfer) and the **NLP processing agents** concurrently.

### C. Graceful Terminations
To stop the stack cleanly:
```bash
docker compose down
```
All containers intercept the `SIGTERM` signal, executing graceful SDK cleanup steps (releasing database locks, deallocating LLM models) in milliseconds.

---

## 4. Running Locally with UV (Development Mode)

If you prefer to run services manually without Docker, synchronize your dependencies first:
```bash
uv sync --all-packages
```

### A. Start API Server
Run the FastAPI gateway server:
```bash
uv run --package api fastapi run packages/api/src/api/main.py --port 8000
```

### B. Run Workspace Agents
All agents are run from the workspace root. Settings are loaded automatically from your `.env` file.

| Agent Package | Main Module | Agent Role |
| :--- | :--- | :--- |
| `euraxess-discovery` | `euraxess_discovery.main` | Pagination crawl discovery (EURAXESS) |
| `academictransfer-discovery` | `academictransfer_discovery.main` | Pagination crawl discovery (AcademicTransfer) |
| `euraxess-sourcing` | `euraxess_sourcing.main` | Page details fetcher (EURAXESS) |
| `academictransfer-sourcing` | `academictransfer_sourcing.main` | Page details fetcher (AcademicTransfer) |
| `lang-detection` | `agent_lang_detection.main` | Language Detection (All Sources) |
| `translation` | `agent_translation.main` | Local NLLB-200 Translation (All Sources) |
| `refinement` | `agent_refinement.main` | Gemma-4 Skills Extraction (All Sources) |
| `matching` | `agent_matching.main` | Candidate CV Matcher & Explainer (All Sources) |

Run any agent using:
```bash
uv run --package <Agent Package> python -m <Main Module>
```
*Example (Matching Worker):*
```bash
uv run --package matching python -m agent_matching.main
```

---

## 5. Configuration Settings

Settings configured via the `.env` file:

| Environment Variable | Default Value | Description |
|---|---|---|
| `API_URL` | `http://localhost:8000` | Target URL of the FastAPI gateway |
| `API_TOKEN` | *None* | Bearer credential token |
| `API_SECRET_KEY` | *None* | Shared validation key (API Server only) |
| `DATABASE_URL` | `sqlite:///jobs.db` | SQL database connection string |
| `EMBEDDING_MODEL` | `nomic-ai/nomic-embed-text-v1.5` | Target SentenceTransformer embedding model name |
| `CRAWL_ONCE` | `false` | If `true`, crawlers execute once and stop. If `false` (default), they loop continuously. |
| `CRAWL_INTERVAL` | `3600` | Period between crawler sweeps in seconds (e.g. `3600` = hourly) |
| `AGENT_POLL_INTERVAL`| `10` | Frequency in seconds that NLP workers poll the API for new tasks |
| `MAX_PAGES` | `5` | Pagination crawl depth |
| `MODEL_PATH` | `unsloth/gemma-4-E2B-it-GGUF/gemma-4-E2B-it-Q4_K_M.gguf` | Path to Gemma-4 GGUF file relative to `MODELS_DIR` |
| `NLLB_MODEL_PATH` | `mijuanlo/nllb-200-distilled-600M-ct2-int8` | Path to NLLB translation model folder relative to `MODELS_DIR` |
| `MODELS_DIR` | `models` | Global folder name to store downloaded models |
| `MAX_LENGTH` | `4096` | LLM maximum generation length |
| `TEMPERATURE` | `0.0` | Model generation temperature |
| `MAX_TEXT_CHARS` | `3000` | Max characters sent to context window |

---

## 6. System Architecture & Diagrams

### Data Flow
Discovery, sourcing, detection, translation, refinement, and matching agents run independently and communicate only with the API server.

```mermaid
graph TD
    subgraph Discovery Nodes
        ED[euraxess-discovery]
        ATD[academictransfer-discovery]
    end

    subgraph Sourcing Nodes
        ES[euraxess-sourcing]
        ATS[academictransfer-sourcing]
    end

    subgraph Gateway Layer
        API[FastAPI Gateway /packages/api]
        DB[(Database SQLite/PostgreSQL)]
    end

    subgraph Language Processing
        LD[lang-detection]
        Trans[translation]
        NLLB[NLLB-200 Local Model]
    end

    subgraph Refinement & Matching
        Refine[refinement]
        GGUF[Gemma-4 GGUF Local Model]
        Match[matching]
    end

    ED -->|POST /jobs stubs| API
    ATD -->|POST /jobs stubs| API

    ES -->|GET /jobs/pending-details| API
    ATS -->|GET /jobs/pending-details| API
    ES -->|PUT /jobs/details| API
    ATS -->|PUT /jobs/details| API

    LD -->|POST /jobs/claim-detect| API
    LD -->|PUT /jobs/detect| API

    Trans -->|POST /jobs/claim-translate| API
    Trans -->|PUT /jobs/translate| API
    Trans -->|Inference request| NLLB

    Refine -->|POST /jobs/claim-refine CAS lease| API
    Refine -->|PUT /jobs/refine upload| API
    Refine -->|Inference request| GGUF

    Match -->|POST /matches/claim| API
    Match -->|PUT /matches/complete| API
    Match -->|POST /matches/claim-explain| API
    Match -->|PUT /matches/complete-explain| API
    
    API <-->|SQLAlchemy ORM| DB
```
