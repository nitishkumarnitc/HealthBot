# HealthBot — System Design Diagram

This document contains a visual system-design diagram (Mermaid) for the HealthBot prototype, followed by concise component descriptions, data flows, scaling notes, and security considerations. Use this as the canonical architecture for initial implementation and team discussion.

---

## Mermaid Diagram (High-level)

```mermaid
flowchart LR
  subgraph Clients
    P[Patient UI (Web/Mobile)]
    C[Clinician Dashboard]
  end

  subgraph Edge
    APIGW[API Gateway / Auth Proxy]
    CDN[CDN]
  end

  subgraph Services
    HB[HealthBot-Core (LangGraph)]
    AUTH[Auth Service]
    SEARCH[Search Service (Tavily)]
    SUM[Summarizer Service]
    QA[QA Service (QGen + Evaluator)]
    VECTOR[Vector Worker]
    CONTENT[Content Service]
    NOTIF[Notification Service]
  end

  subgraph Data
    RDS[(Postgres / RDS)]
    REDIS[(Redis - session cache)]
    VDB[(Vector DB)]
    S3[(S3 - artifacts & docs)]
    LOG[(Observability - Prom/Grafana/OTel)]
  end

  P -->|HTTPS| CDN --> APIGW
  C -->|HTTPS| APIGW
  APIGW --> AUTH
  APIGW --> HB
  HB --> SEARCH
  HB --> SUM
  HB --> QA
  HB --> REDIS
  HB --> VDB
  SEARCH -->|external API| Tavily[(Tavily Search API)]
  SUM -->|LLM| OpenAI[(OpenAI / LLM Provider)]
  QA -->|LLM| OpenAI
  VECTOR --> VDB
  CONTENT --> RDS
  AUTH --> RDS
  HB --> S3
  HB --> LOG
  ALL[All Services] --> LOG
```

---

## Component Descriptions

* **Patient UI**: React/Next.js app or mobile wrapper. Talks to API Gateway for secured endpoints. Uses CDN for static assets.

* **Clinician Dashboard**: Web app to author/curate content, review analytics, and manage QA questions.

* **API Gateway**: Handles authentication (JWT / OIDC), rate-limiting, request validation, and routing to backend services.

* **HealthBot-Core (LangGraph)**: Orchestrates the workflow — receives user intent, orchestrates search -> summarizer -> quiz generation -> evaluation -> response.

* **Search Service**: Thin adapter to Tavily; implements caching and result normalization.

* **Summarizer Service**: Calls LLM (OpenAI or equivalent) to rewrite content into patient-friendly summaries.

* **QA Service**: Generates quiz questions and evaluates answers. Uses LLM for generation and optionally a smaller model or heuristic for fast grading.

* **Vector Worker / Vector DB**: Generates embeddings for curated content and stores them for semantic search (optional for improved relevance).

* **Content Service**: Stores curated content, metadata, editorial workflow, and clinician-authored resources.

* **Notification Service**: Push/email/sms for reminders or follow-ups.

* **Storage & Cache**: Postgres for relational data, Redis for session/state with TTL, S3 for artifacts and documents, Vector DB for embeddings.

* **Observability**: OpenTelemetry traces, Prometheus metrics, Grafana dashboards, centralized logging (ELK/CloudWatch).

---

## Data Flow (User Scenario)

1. Patient requests information (topic) via UI.
2. API Gateway authenticates and forwards to HealthBot-Core.
3. HealthBot-Core checks Redis cache; if miss, calls Search Service (Tavily) to fetch sources.
4. Results are normalized; HealthBot calls Summarizer to create patient-friendly content.
5. Summary stored to Redis (session) and optionally to RDS (anonymized audit record) and S3.
6. Patient views summary and requests quiz; HealthBot calls QA Service to generate a single question.
7. Patient submits answer; QA Service evaluates using LLM + heuristics, returns grade and explanation with citations to the summary.
8. Session state kept in Redis and cleared when user starts a new topic or after TTL.
9. Events emitted to Observability and optional analytics pipelines.

---

## Scaling & Resilience Notes

* Keep services stateless; scale via K8s HPA or serverless containers.
* Use managed RDS and managed vector DB for operational simplicity.
* Cache frequent search results and generated summaries in Redis with short TTLs to reduce LLM / Tavily calls.
* Queue heavy work (vector embedding generation, batch indexing) to background workers.
* Implement circuit breakers and exponential backoff for Tavily & LLM calls.

---

## Security & Privacy Considerations

* Enforce TLS everywhere; use mTLS between services if possible.
* Use a secrets manager for API keys and DB credentials.
* Store PII/PHI only when necessary; prefer ephemeral session storage and anonymized audit logs.
* Implement RBAC on clinician dashboard and least-privilege IAM for services.
* Ensure HIPAA compliance if handling PHI: BAAs, audit logs, encryption at rest & transit.

---

## Next Steps

* Convert this mermaid diagram to draw.io or Figma for visual polish.
* Produce a Deployment diagram (K8s manifests + infra IaC snippets).
* Create sequence diagrams for critical flows (search -> summarize -> quiz -> evaluate).

---

*End of System Design Diagram document.*
