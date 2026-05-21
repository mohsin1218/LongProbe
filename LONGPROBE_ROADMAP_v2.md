# LongProbe Product Roadmap v2

Planned features and milestones for growing LongProbe into the go-to RAG regression testing harness.

> **Research basis (May 2026):** 60% of RAG deployments now include systematic evaluation from day one.
> LongProbe's deterministic, sub-second, local-first approach has no direct competitor —
> RAGAS, DeepEval, TruLens, and LangSmith are all LLM-heavy, slow, and cloud-dependent.
> This roadmap closes three critical gaps the first version missed:
> corpus poisoning detection, production-to-test feedback loops, and hybrid retrieval testing.

---

## v0.1.x — Core Stability ✅ Shipped

- [x] Sub-second deterministic regression engine (`longprobe check`)
- [x] Golden Question definition format (YAML/JSON)
- [x] SQLite baseline snapshots (local, zero external dependencies)
- [x] Three resilient match modes: Exact ID, Text Substring, Semantic Similarity
- [x] Recall Score computation and colored diff output on failure
- [x] `longprobe generate --capture --auto` — LLM-powered zero-effort test generation
- [x] Universal HTTP Adapter — test entire RAG APIs end-to-end
- [x] Tag-based scoping (`--tag doc:billing`)
- [x] GitHub Actions output (`--output github`) — annotate PRs, block merges on regression
- [x] PyPI package published

---

## v0.2.0 — Developer Experience 🔧 Current

Frictionless inner dev loop: faster feedback, better ergonomics, zero-config onboarding.

- [x] `longprobe watch` — file-system watcher that auto-reruns checks on code save
- [x] `[tool.longprobe]` config block in `pyproject.toml` — zero extra config files
- [x] Async check support — `longprobe check --async` for high-concurrency API testing
- [ ] Interactive golden question editor (`longprobe edit`) — TUI to browse, edit, and approve captured baselines
- [ ] Pytest plugin (`pytest-longprobe`) — `@longprobe_check` decorator to embed retrieval assertions in existing test suites
- [ ] `longprobe explain` — on failure, prints a human-readable summary: chunk distance delta, rank change, why it dropped
- [ ] `--threshold` flag — configurable recall pass/fail threshold (e.g., `--threshold 0.85`) instead of binary pass/fail
- [ ] `longprobe diff <baseline-a> <baseline-b>` — compare any two snapshot versions side-by-side

---

## v0.3.0 — Framework & Vector DB Integrations 🔌

Native connectors so teams test at any layer without writing custom adapters.

- [ ] **LangChain** adapter — direct hooks into Chroma, FAISS, Qdrant, Weaviate, Pinecone
- [ ] **LlamaIndex** adapter — query engine and retriever-level testing
- [ ] **LangGraph** adapter — agentic RAG pipeline step-level regression
- [ ] **Haystack** adapter
- [ ] **OpenAI Assistants API** adapter — test file-search retrieval in Assistant threads
- [ ] **LongParser + LongTrainer** native integration — zero-config when used in the EnDevSols Long Suite
- [ ] **CrewAI / AutoGen** adapters — test retrieval inside multi-agent workflows
- [ ] Direct vector DB connectors: Qdrant, Weaviate, Pinecone, Milvus — bypass HTTP, hit the store directly
- [ ] **LongProbe SDK** — programmatic Python API (`from longprobe import Probe`) for teams that prefer code over CLI

---

## v0.4.0 — Observability, Analytics & Production Feedback Loop 📊

> **Key addition vs. v1 roadmap:** The production-to-test feedback loop.
> The best evaluation tools in 2026 convert production failures directly into new test cases.
> LongProbe must close this loop — not just test before deployment but learn from production.

- [ ] Dashboard UI (`longprobe dashboard`) — web interface: baselines, recall trends, failure history across projects
- [ ] Recall trend charts — track Recall@K over time per question, per tag, per project
- [ ] **Production query capture** — `longprobe capture --from-logs` ingests production query logs and flags queries with low recall against current baselines
- [ ] **Auto-golden set expansion** — one-click promotion of a flagged production failure into a new golden question, closing the prod-to-test loop
- [ ] Alerting — Slack/email/webhook when recall drops below threshold in CI or production
- [ ] **Golden set staleness detection** — alert when the distribution of real user queries has drifted significantly from the golden question set, signaling the test suite needs updating
- [ ] Multi-project support — manage golden question sets for multiple RAG pipelines from one config
- [ ] HTML + JSON report export — shareable regression reports for stakeholders
- [ ] OpenTelemetry export — send LongProbe spans to Jaeger, Grafana, Datadog
- [ ] **Cloud baseline storage (Team tier)** — shared baselines without Git LFS or shared filesystems; audit log of all mutations

---

## v0.5.0 — Hybrid Retrieval, Agentic & Security Testing 🔐🤖

> **Three new additions vs. v1 roadmap based on 2026 research gaps:**
> (1) Hybrid retrieval testing — production stacks combine dense + BM25 + graph.
> (2) Adversarial/poisoning tests — corpus poisoning is now a top-10 OWASP LLM risk.
> (3) Agentic multi-hop testing — RAG is no longer a single-step retrieval.

### Hybrid & Advanced Retrieval
- [ ] **Hybrid retrieval testing** — assert recall across dense + BM25 + keyword ensembles; detect when one leg of the hybrid silently degrades
- [ ] **Late interaction support (ColBERT/ColBERTv2)** — token-level MaxSim matching for pipelines using late interaction retrievers
- [ ] **Reranker regression testing** — assert that critical chunks survive reranking stages (Cohere, cross-encoder); not just initial retrieval
- [ ] **Context window-aware testing** — detect when a chunk is retrieved but buried so deep in a 1M-token context it is effectively lost

### Agentic & Multimodal
- [ ] **Multi-hop golden questions** — define expected retrieval chains (Q1 → chunk A → Q2 → chunk B) for agentic pipelines
- [ ] **GraphRAG support** — golden assertions on entity/relation subgraphs (Microsoft GraphRAG, LightRAG)
- [ ] **Multimodal chunk matching** — test retrieval of image chunks, table segments, and PDF page extracts (not just text)
- [ ] **Tool-use retrieval tracing** — in agentic settings, verify that tool calls return expected grounding chunks before generation

### Security & Adversarial Testing
- [ ] **Corpus poisoning detection** — `longprobe scan --poison` checks whether any top-K results for golden questions contain statistically anomalous similarity scores (a signal of BadRAG-style adversarial passages)
- [ ] **Retrieval backdoor regression** — define "forbidden chunks" that should never appear in results for a given query; alert if they surface after a data update
- [ ] **Data-push regression** — automatically run a LongProbe check after every document ingestion to detect vector space pollution from new content

---

## v0.6.0 — Enterprise Features 🏢

- [ ] Role-based access for baseline storage — write vs. read-only separation
- [ ] Full audit log for all baseline mutations and check runs
- [ ] PII redaction in stored baselines — scrub sensitive content from golden chunk snapshots before committing
- [ ] SLA-aware check mode — skip semantic matching if latency budget is exceeded, fall back to ID/substring
- [ ] SSO / SAML integration for dashboard
- [ ] Compliance-mode export — SOC 2 / HIPAA audit-ready reports
- [ ] **Domain-expert golden question mode** — non-technical SMEs (doctors, lawyers, finance analysts) define expected retrieval outcomes in plain language; LongProbe translates to formal test cases

---

## Future Considerations 🔭

- **Fine-tuned semantic matching** — domain-specific models for medical, legal, financial RAG where general cosine similarity is unreliable
- **Multilingual golden questions** — regression testing for non-English RAG pipelines
- **LLM-as-judge fallback** — optional GPT/Claude verification for low-confidence semantic matches only
- **VS Code extension** — inline recall status per golden question while editing chunking or embedding code
- **LongProbe Cloud SaaS** — hosted tier with team dashboards and PR integration, no self-hosting required

---

## Release Cadence

| Version | Target        | Focus                                             | Status      |
|---------|--------------|---------------------------------------------------|-------------|
| v0.1.x  | Shipped       | Core engine, CLI, CI/CD hooks                     | ✅ Done      |
| v0.2.0  | Now           | Developer experience & inner-loop speed           | 🔧 Current  |
| v0.3.0  | 2–3 months   | Framework & vector DB integrations, SDK           | 📋 Planned  |
| v0.4.0  | 4–5 months   | Observability, analytics, prod-to-test loop       | 📋 Planned  |
| v0.5.0  | 6–8 months   | Hybrid retrieval, agentic, security testing       | 🔭 Future   |
| v0.6.0  | 10–12 months | Enterprise: compliance, RBAC, domain-expert mode  | 🔭 Future   |

---

## What Changed from v1 Roadmap — and Why

| Area | v1 Roadmap | v2 Roadmap | Reason |
|------|------------|------------|--------|
| Security | Not mentioned | v0.5.0 full milestone | BadRAG research: 0.04% corpus poisoning → 98% hijack success rate |
| Prod feedback loop | Missing | v0.4.0 core feature | Leading tools in 2026 all converge on prod-failures → test-cases loop |
| Hybrid retrieval | Missing | v0.5.0 | Dense+BM25+graph hybrid is now the production standard, not the exception |
| Enterprise | v0.6.0 only | Cloud baselines moved to v0.4.0 | Paying teams need shared baselines before month 10 |
| Golden set staleness | "Future" | v0.4.0 | Drift detection is not optional once prod query logs are available |
| LongProbe SDK | Missing | v0.3.0 | Teams with complex setups need programmatic access, not just CLI |

---

## Competitive Moat (May 2026)

| Tool          | Approach                  | Speed        | LLM Cost | Local-First | Regression Diffs | Poison Detection |
|---------------|---------------------------|-------------|----------|-------------|------------------|-----------------|
| **LongProbe** | Deterministic chunk match | Sub-second  | None     | ✅ Yes      | ✅ Yes           | ✅ v0.5.0       |
| DeepEval      | Pytest + LLM judge        | Minutes     | High     | ❌ No       | ❌ No            | ❌ No           |
| RAGAS         | Reference-free metrics    | Minutes     | High     | ❌ No       | ❌ No            | ❌ No           |
| TruLens       | LLM feedback triad        | Minutes     | High     | ❌ No       | ❌ No            | ❌ No           |
| LangSmith     | Trace observability       | Real-time   | Medium   | ❌ No       | ❌ No            | ❌ No           |
| Arize Phoenix | Open-source observability | Real-time   | Low      | Partial     | ❌ No            | ❌ No           |

**LongProbe's moat:** The only tool that answers *"did my last commit break retrieval?"* in milliseconds with zero LLM cost — and the only tool building toward *"has my corpus been poisoned?"*
