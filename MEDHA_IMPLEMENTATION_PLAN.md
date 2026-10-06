# MEDHA Implementation Plan

## 1. Current architecture

This repository already contains a partially implemented Medha system and is not a blank slate. The current codebase is organized around a FastAPI backend and a React/Vite frontend.

### Observed structure

- Backend runtime: [backend/main.py](./backend/main.py)
- Frontend app: [frontend/src/App.jsx](./frontend/src/App.jsx)
- Local language understanding: [backend/brain/local_nlu.py](./backend/brain/local_nlu.py)
- Memory layers: [backend/memory/manager.py](./backend/memory/manager.py), [backend/memory/layers.py](./backend/memory/layers.py)
- Conversation engine: [backend/brain/conversation.py](./backend/brain/conversation.py)
- Knowledge layer: [backend/knowledge/knowledge_base.py](./backend/knowledge/knowledge_base.py)
- Search layer: [backend/search/search_manager.py](./backend/search/search_manager.py)
- Authority and override: [backend/core/authority.py](./backend/core/authority.py), [backend/core/policy.py](./backend/core/policy.py), [backend/core/OVERRIDE.md](./backend/core/OVERRIDE.md)
- Auth and sessions: [backend/api/auth.py](./backend/api/auth.py), [backend/auth/security.py](./backend/auth/security.py), [backend/chats/store.py](./backend/chats/store.py)
- Model architecture foundations: [backend/model](./backend/model)

### Working functionality already present

- Basic FastAPI app with CORS, health endpoint, memory endpoint, and auth/chats routers.
- SQLite-backed user, chat, and message persistence.
- Password hashing with PBKDF2 and signed JWT-like tokens.
- Local NLU intent classification using TF-IDF + logistic regression.
- Multi-layer memory model with personal, temporary, permanent, and knowledge scopes.
- Local search / knowledge retrieval pipeline with resource and web-based fallback behavior.
- Auth UI and chat UI with login/register/reset flows, multi-chat management, message history, and rename/delete chat actions.
- Local model architecture modules for attention, embeddings, transformer blocks, positional encoding, and tokenizer scaffolding.
- A creator/host authority design with an override file and permission policy that explicitly protects the host.

## 2. Existing functionality

### Backend

- FastAPI API exposes `/api/chat`, `/api/chats`, `/api/auth`, `/api/memory`, `/api/health` and a desktop/authority surface.
- App bootstraps chat tables and memory tables on startup.
- Conversation engine stores user/assistant turn metadata and can store memory based on intent classification and memory evaluation.
- Memory management supports memory learning, search, and retention rules.
- Search manager routes queries through local resource, Wikipedia, and web search providers.

### Frontend

- React + Vite UI supports:
  - sign-in / create account / reset password
  - multiple chat sessions
  - rename and delete chats
  - persistent local token handling
  - message styling and chat flow
  - sidebar actions for account and recovery

### Security and authority

- [backend/core/OVERRIDE.md](./backend/core/OVERRIDE.md) exists and declares the authority hierarchy.
- [backend/core/authority.py](./backend/core/authority.py) defines creator/host authority and permission checks.
- Auth code prevents plain-text credential storage and uses secure password hashing.

## 3. Missing functionality

The repository contains foundational modules, but key Medha specification items are still missing or incomplete.

### Major gaps

- No root-level architecture/implementation documentation beyond the generated audit file.
- No formal `ARCHITECTURE.md`, `SECURITY.md`, `MEMORY.md`, `TOOLS.md`, or `DEVELOPMENT.md` files.
- No explicit identity configuration files under `backend/core/identity/`.
- No complete task system with persisted metadata, deadlines, subtasks, and histories.
- No real tool registry with permission envelopes, risk scoring, or audit metadata.
- No audit system with append-safe logs and protected storage.
- No subagent framework despite the architecture description.
- No explicit context-priority retrieval system that selects relevant memory, file, and tool context per request.
- No real long-running planner/agent loop with iteration caps, cancellation, and verification enforcement.
- No complete resource ingestion pipeline with indexing, chunking, metadata, embeddings, and change detection.
- No database abstraction layer and migration system beyond ad hoc SQLite schema creation.
- No dedicated repository-oriented project memory or local resource knowledge indexing to reflect the user’s project and files.
- No complete web research workflow with ranking and source reliability scoring.
- No comprehensive permission model for filesystem, terminal, browser, git, desktop, and network control.

## 4. Broken functionality

### Test/status problems

The current automated test setup is not ready for consistent validation.

- `pytest -q backend` fails during collection because the project is not installed as a package and tests are not valid pytest tests.
- [backend/brain/test_conversation.py](./backend/brain/test_conversation.py) is an interactive script with `input()` and an infinite loop, so it cannot run under pytest without `-s` and is not a real test case.
- [backend/knowledge/test_knowledge.py](./backend/knowledge/test_knowledge.py) is also a script and not a proper test.
- The repo has model unit tests, but they are not exercised in a package-aware or CI-friendly way.
- The frontend build passes when executed with PowerShell execution policy bypassed: `npm run build` succeeds in Vite.

### Operational risks

- `backend.main` imports many live subsystems without a structured startup validation or feature gate.
- Several modules are implemented as “best effort” components, but not validated under a clean runtime configuration.
- Some functionality is likely to be incomplete or fragile because a few modules remain scaffolds rather than production-ready services.

## 5. Security issues and gaps

The project already contains some security hygiene, but the implementation is still not complete for the Medha specification.

### Existing strengths

- PBKDF2 password hashing.
- Signed JWT-like tokens with expiration.
- Override hierarchy and host protection policy.
- No hard-coded runtime LLM key is required to run the local architecture.

### Gaps

- No central security policy enforcement layer outside the simple `AuthorityPolicy` and `OVERRIDE.md` checks.
- No deterministic command validation before terminal execution.
- No path traversal guard around file operations.
- No explicit CORS/csrf/session hardening beyond the current start-up config.
- No secret manager or `.env` governance beyond examples.
- No protect-on-write audit layer for privileged actions.
- No prompt injection or malicious document filtering at the system boundary.
- No robust user role separation beyond the basic `creator`, `user`, and `host` distinctions.

## 6. Proposed architecture

The future architecture should remain local-first and replaceable at the model layer while preserving Medha as a persona and system.

### Target layout

```text
backend/
  api/
  auth/
  brain/
  chats/
  core/
    identity/
    security/
    memory/
    planner/
    tools/
    audit/
    OVERRIDE.md
  database/
  knowledge/
  memory/
  model/
  security/
  services/
  tests/
  main.py
frontend/
  src/
```

### Architectural goals

- Keep the model layer modular and replaceable.
- Separate identity, security, memory, planning, tools, and audit from model implementation.
- Preserve the creator/host authority hierarchy as a hard constraint.
- Treat all web and file content as untrusted unless explicitly approved.
- Use selective context retrieval instead of sending all memory to the model.

## 7. Database changes

### Current state

SQLite is used directly in multiple places, including [backend/chats/store.py](./backend/chats/store.py) and [backend/memory/layers.py](./backend/memory/layers.py). This is workable for a prototype, but it is not a clean long-term Medha architecture.

### Proposed database design

Add a consistent repository layer with explicit domain tables:

- `users`
- `conversations`
- `messages`
- `memories`
- `memory_events`
- `tasks`
- `task_history`
- `tool_permissions`
- `audit_logs`
- `knowledge_sources`
- `documents`
- `embeddings`

### Database strategy

- Keep SQLite for local-first development.
- Introduce repository/service abstractions behind a unified database module.
- Add migration scripts and schema version tracking.
- Prevent ad hoc schema creation in unrelated modules.
- Store safe metadata only; never write secrets or tokens into logs or DB tables.

## 8. Backend changes

### Required backend work

1. Consolidate API routes under a documented backend contract.
2. Formalize identity and security configuration with clear creator/host approval rules.
3. Split business logic into stable services rather than ad hoc module calls.
4. Build a persistent task manager with statuses such as `TODO`, `IN_PROGRESS`, `BLOCKED`, `COMPLETED`, and `CANCELLED`.
5. Add structured error handling with error codes, recoverability, and safe user-facing messaging.
6. Add central audit and observability modules.
7. Introduce permissions and capability gates for files, network, desktop, terminal, and destructive actions.
8. Support prompt-injection safeguards and malicious content filters.
9. Add a proper repository-aware document resource model.

### Priority backend targets

- [backend/main.py](./backend/main.py)
- [backend/api](./backend/api)
- [backend/core](./backend/core)
- [backend/memory](./backend/memory)
- [backend/brain](./backend/brain)
- [backend/tools](./backend/tools)
- [backend/security](./backend/security)

## 9. Frontend changes

### Current state

The frontend already provides a usable chat and auth interface.

### Required next steps

- Add clear memory, tasks, tool activity, and agent status panels.
- Provide visible conversation search and chat history management.
- Keep the user experience minimal and practical, without unnecessary animation.
- Add global error banner / observability style feedback.
- Separate chat data, memory data, and tool data states to avoid mixing UI concerns.
- Introduce a settings area for permission visibility and account controls.

## 10. Memory architecture

The current memory system is promising but should evolve into a true memory architecture.

### Current implementation

- `personal`, `temporary`, `permanent`, and `knowledge` scopes in [backend/memory/layers.py](./backend/memory/layers.py)
- `MemoryManager` wrapper in [backend/memory/manager.py](./backend/memory/manager.py)
- Search and retrieval support in [backend/memory/semantic_memory.py](./backend/memory/semantic_memory.py)

### Target memory model

- Working memory: active request context, current task, and tool state
- Episodic memory: events and user interactions over time
- Semantic memory: learned concepts and project understanding
- Personal memory: user preferences and stable traits
- Relationship memory: recurring interaction style and preferences
- Procedural memory: task and workflow patterns
- Knowledge memory: document and local-resource-derived facts

### Required behaviors

- Distinguish fact, preference, task, event, assumption, and uncertain information.
- Manage memory correction and override precedence.
- Support archival and cleanup after six months when relevance is low.
- Maintain source, timestamp, confidence, and provenance metadata.

## 11. Agent architecture

### Current state

The project contains some early agent planning and permissions logic, including:

- [backend/agent/planner.py](./backend/agent/planner.py)
- [backend/agent/permissions.py](./backend/agent/permissions.py)
- [backend/agent/tasks.py](./backend/agent/tasks.py)

### Required next steps

- Build an explicit `OBSERVE -> THINK -> PLAN -> ACT -> VERIFY -> CONTINUE/STOP` loop.
- Add maximum iteration caps and timeout protections.
- Require capability checks before every tool call.
- Ensure all actions have audit records and safe rollback/confirmation logic.
- Separate planner from executor and verifier.
- Define clear parent/subagent boundaries and privilege limits.

## 12. Tool architecture

### Current state

There is a basic `backend/tools` structure but it is not yet fully formalized.

### Required tool registry

Each tool should define:

- name
- description
- input schema
- output schema
- permission level
- risk level
- audit requirements

### Target tool categories

- filesystem
- terminal
- git
- browser
- desktop
- database
- search

Sensitive tools must be gated by capability and require explicit permission.

## 13. Testing strategy

The current test suite is not in a production-ready state.

### Immediate actions

- Replace script-style tests with actual `pytest` tests or `unittest` test cases.
- Ensure all imports work from the repository root.
- Add CI-friendly test discovery for backend and frontend.
- Add tests for security, memory, auth, tool permissions, and conversation flows.

### Minimum categories

- unit tests
- integration tests
- API tests
- memory tests
- security tests
- tool tests
- agent-loop tests
- frontend tests

### Required security tests

- prompt injection attempts
- path traversal
- unauthorized tool use
- permission escalation
- secret leakage
- self-modification attempts
- malicious local document handling
- malicious web content handling

## 14. Implementation phases

### Phase 1 — Foundation

- finalize repo structure and explicit docs
- stabilize backend startup and import paths
- align config and dependency management
- validate backend and frontend health checks

### Phase 2 — Conversation

- persistent multi-chat support
- message persistence and retrieval
- rename/delete/history state
- context management improvements

### Phase 3 — Memory

- complete memory lifecycle
- explicit memory correction workflow
- retrieval weighting and contextual recall
- improved local knowledge indexing

### Phase 4 — Knowledge

- resource ingestion
- document indexing and chunking
- metadata and retrieval quality improvements
- source tracking and confidence scoring

### Phase 5 — Agent

- planner
- task manager
- verification loop
- tool gating
- execution limits and cancellation

### Phase 6 — Tools

- filesystem / terminal / git / browser / database controls
- permission enforcement
- safe execution boundaries

### Phase 7 — Security

- authority policy enforcement
- audit reports
- prompt injection protections
- destructive-command safeguards

### Phase 8 — Intelligence layer

- local model abstraction
- embeddings and retrieval improvements
- future ML model replacement

### Phase 9 — Advanced agent capabilities

- subagents
- long-running tasks
- specialized expert agents
- cross-tool orchestration

## 15. Dependencies

### Current dependencies already reflected in the repo

- Python: FastAPI, Uvicorn, requests, scikit-learn, joblib, PyPDF2, python-docx, python-pptx, torch
- Frontend: React, Vite, ESLint, concurrent script support
- Local-first approach: no mandatory external LLM runtime for core Medha behavior

### Additional dependencies likely needed for the target spec

- database migration tooling
- testing framework standardization
- optional vector DB or SQLite vector extension strategy
- richer observability tooling
- stricter security libraries for session and rate-limit handling

## 16. Risks

- Architectural drift: parts of the system are already written but not aligned to a single canonical design.
- Mixed scope: conversation features, memory system, security, and local model components are all active but not coherently integrated.
- Test fragility: interactive scripts are being treated like tests, which masks real failures.
- Permission ambiguity: the repo has authority concepts but not a full framework for real runtime enforcement.
- Long-term maintainability: ad hoc SQLite writes and manual schema updates can cause drift.

## 17. Migration strategy

1. Freeze the current working codebase and perform a repo-wide audit.
2. Normalize imports and package configuration.
3. Standardize backend and frontend startup commands.
4. Add migration-friendly database schema management.
5. Move from ad hoc modules to service/repository boundaries.
6. Introduce a verification suite before deep architectural changes.
7. Implement memory, agent, and tool improvements incrementally.
8. Preserve host and creator authority rules throughout all phases.
9. Only then add advanced features such as subagents and long-running orchestration.

## 18. Recommended action and approval gate

This repository has enough foundational work to justify a real Medha implementation plan, but it is not yet ready for broad architectural rewriting.

The safest next step is:

- keep the current code as a base,
- formalize the architecture around the required Medha principles,
- fix the testing and package readiness problems,
- then implement the missing, security-sensitive foundation incrementally.

No major rewrite should proceed until this plan is approved by the creator/host.

## 19. Summary

The repo is materially stronger than a prototype, but the current system is a partial foundation rather than a complete Medha implementation. Current strengths are local-first architecture, memory scaffolding, auth, and chat UI. Current weaknesses are formalized testing, tool/security maturity, migration discipline, and end-to-end architecture consistency.

The key objective is not to build a chatbot. The objective is to build a controlled, auditable, persistent personal AI system whose memory, tools, identity, authority, and model layer remain separable.
