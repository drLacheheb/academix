# Academic Job Sourcing & Refinement

A Python workspace to fetch, parse, and refine academic job listings from EURAXESS and AcademicTransfer.

---

## 1. Project Structure

```text
├── packages/
│   ├── core/                          # Shared models, repository, and HTTP client
│   ├── api/                           # FastAPI gateway server
│   └── agents/                        # Isolated worker packages
│       ├── euraxess-discovery/            # EURAXESS search pagination worker
│       ├── euraxess-sourcing/             # EURAXESS page details fetcher
│       ├── academictransfer-discovery/    # AcademicTransfer search pagination worker
│       ├── academictransfer-sourcing/     # AcademicTransfer page details fetcher
│       ├── lang-detection/                # Standalone local language detection worker
│       ├── translation/                   # Standalone local NLLB-200 translation worker
│       └── refinement/                    # Local ONNX model metadata refiner
├── pyproject.toml                     # Root workspace configuration
├── uv.lock                           # Workspace dependency lockfile
├── .env.example                       # Settings template file
└── Dockerfile                         # API gateway Dockerfile
```

---

## 2. Requirements

*   **Python**: `>= 3.11`
*   **Environment Manager**: [uv](https://github.com/astral-sh/uv) (recommended)
*   **Hardware requirements**:
    *   **Refinement Agent**: ~3GB RAM / VRAM to load the `phi-4-mini` ONNX model.
    *   **Translation Agent**: ~600MB RAM to load the quantized `NLLB-200-distilled-600M` model.
*   **Database**: SQLite (default local file `jobs.db`) or PostgreSQL (e.g., Neon).

---

## 3. Quick Start

### A. Configure Environment
Create a local `.env` file from the template:
```bash
cp .env.example .env
```
Edit the `.env` file to configure your credentials and database connection string.

### B. Install Dependencies
Synchronize the workspace:
```bash
uv sync --all-packages
```

### C. Start API Server
Run the FastAPI gateway server:
```bash
uv run --package api fastapi run packages/api/src/api/main.py --port 8000
```

---

## 4. Running Workspace Agents

All agents are run from the workspace root. Settings are loaded automatically from the `.env` file.
The agents are fully decoupled and communicate only with the central API gateway.

### Agents Catalog

| Agent Package | Main Module | Agent Role | Target Source |
| :--- | :--- | :--- | :--- |
| `euraxess-discovery` | `euraxess_discovery.main` | Discovery | EURAXESS |
| `academictransfer-discovery` | `academictransfer_discovery.main` | Discovery | AcademicTransfer |
| `euraxess-sourcing` | `euraxess_sourcing.main` | Sourcing | EURAXESS |
| `academictransfer-sourcing` | `academictransfer_sourcing.main` | Sourcing | AcademicTransfer |
| `lang-detection` | `agent_lang_detection.main` | Language Detection | (All Sources) |
| `translation` | `agent_translation.main` | Local Translation | (All Sources) |
| `refinement` | `agent_refinement.main` | Metadata Extraction | (All Sources) |

### Command Syntax
Run any agent by specifying its package and module:
```bash
uv run --package <Agent Package> python -m <Main Module>
```

*Example:*
```bash
uv run --package lang-detection python -m agent_lang_detection.main
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
| `MAX_PAGES` | `5` | Pagination crawl depth |
| `MODEL_PATH` | `phi-4-mini-onnx/...` | Relative path to local ONNX model directory |
| `MAX_LENGTH` | `4096` | LLM maximum generation length |
| `TEMPERATURE` | `0.0` | Model generation temperature |
| `MAX_TEXT_CHARS` | `3000` | Max characters sent to context window |
| `AGENT_NAME` | `refinement-worker` | Custom agent identifier for locking |

---

## 6. System Architecture & Diagrams

### Data Flow
Discovery, sourcing, detection, translation, and refinement agents communicate only with the API server.

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

    subgraph Refinement Nodes
        Refine[refinement]
        ONNX[Phi-4-mini ONNX Local Model]
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
    Refine -->|Inference request| ONNX
    API <-->|SQLAlchemy ORM| DB
```

### Class Structures
Shared models and interfaces reside in the core package.

```mermaid
classDiagram
    class BaseHttpClient {
        <<Interface>>
        +fetch(url: str)* bytes
        +close()* void
    }
    class HttpClient {
        +fetch(url: str) bytes
        +close() void
    }
    class BaseDiscovery {
        <<Abstract>>
        +http_client: BaseHttpClient
        +max_pages: int
        +search_all(known_urls: set) list
        #_build_browse_url(page: int)* str
        #_parse_search_page(html_content: str)* list
    }
    class BaseSourcing {
        <<Abstract>>
        +http_client: BaseHttpClient
        +source_detail(url: str) JobDetailUpdate
        #_parse_detail_page(html_content: str, url: str)* JobDetailUpdate
    }
    class EuraxessDiscovery {
        +SOURCE_NAME: str
        #_build_browse_url(page: int) str
        #_parse_search_page(html_content: str) list
    }
    class EuraxessSourcing {
        +SOURCE_NAME: str
        #_parse_detail_page(html_content: str, url: str) JobDetailUpdate
    }
    class AcademicTransferDiscovery {
        +SOURCE_NAME: str
        #_build_browse_url(page: int) str
        #_parse_search_page(html_content: str) list
    }
    class AcademicTransferSourcing {
        +SOURCE_NAME: str
        #_parse_detail_page(html_content: str, url: str) JobDetailUpdate
    }
    class BaseRefiner {
        <<Abstract>>
        +refine(url: str, title: str, description: str, requirements: str)* RefinementResult
    }
    class LlmRefiner {
        -_system_prompt: str
        -_model_path: str
        +load_model() void
        +refine(url: str, title: str, description: str, requirements: str) RefinementResult
    }
    class DatabaseJobRepository {
        -_SessionLocal: sessionmaker
        +save(jobs: list) void
        +claim_next_for_refinement(agent_name: str) Job
        +complete_refinement(url: str, required_skills: list, education_level: str) void
        +fail_refinement(url: str) void
    }
    class Job {
        +title: str
        +url: str
        +source: str
        +deadline: str
        +employer: str
        +location: str
        +description: str
        +requirements: str
        +required_skills: list
        +education_level: str
    }

    BaseHttpClient <|-- HttpClient
    BaseDiscovery ..> BaseHttpClient : Uses
    BaseSourcing ..> BaseHttpClient : Uses
    BaseDiscovery <|-- EuraxessDiscovery
    BaseDiscovery <|-- AcademicTransferDiscovery
    BaseSourcing <|-- EuraxessSourcing
    BaseSourcing <|-- AcademicTransferSourcing
    BaseRefiner <|-- LlmRefiner
    DatabaseJobRepository ..> Job : Manages
    EuraxessSourcing ..> Job : Sources Details
    AcademicTransferSourcing ..> Job : Sources Details
    LlmRefiner ..> Job : Refines
```
