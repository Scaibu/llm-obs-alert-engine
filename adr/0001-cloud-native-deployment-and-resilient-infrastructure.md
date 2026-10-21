# ADR 0001: Cloud-Native Multi-Target Deployment & Resilient Infrastructure Architecture for Alert Engine

- **Status:** Accepted
- **Date:** 2026-10-21
- **Scope:** `alert-engine` (`deploy/`, `database/`, `messaging/`, `config/`), Central Platform Infrastructure (`llmobs-network`)
- **Author:** Principal Distributed Systems Architect & Infrastructure Security Officer

---

## 1. Context and Problem Statement: Why Does This Even Exist?

In high-throughput, low-latency LLM observability platforms, the `alert-engine` is the mission-critical incident dispatch, anomaly detection, and routing control plane. It operates continuously at the boundary between high-velocity asynchronous stream ingestion and synchronous external incident management systems. 

The service ingests streaming events across six primary Kafka event topics:
1. `alerts.budget`: Real-time tenant token budget exhaustion alerts emitted by `budget-provisioner` and `event-cost`.
2. `alerts.cost.anomaly`: Multi-sigma EWMA cost spikes and runaway token consumption patterns.
3. `llm.toxicity.flagged`: Safety guardrail breach detections and toxic prompt/completion flags from `toxicity`.
4. `alerts.quality.degradation`: Semantic drift, coherence erosion, and perplexity degradation events from `quality-engine`.
5. `alerts.latency.slo`: Sliding-window p95/p99 service-level objective breach events from `latency-engine` and `slo-burn-worker`.
6. `alerts.latency.ttft_regression`: Time-To-First-Token regression alarms flagging severe LLM provider degradation.

The engine must evaluate threshold rules against business invariants, enforce distributed token-bucket and sliding-window rate limits in Redis, maintain deduplicated relational incident state and audit history in AlloyDB/PostgreSQL, resolve GitOps ownership mappings, and dispatch prioritized notifications to external webhooks (Slack incoming webhooks, PagerDuty Events API v2) while emitting OpenTelemetry metrics and traces.

Historically, across the early iterations of this monorepo, microservices lacked declarative, unified infrastructure definitions. Deployment configurations were scattered across ad-hoc Docker files, hand-crafted shell scripts, unversioned Kubernetes manifests, and unmanaged networking bridges. This led to severe operational breakdowns, silent incident masking, security vulnerabilities, and prolonged production outages.

---

### 1.1 Post-Mortem Analysis of Past Systemic Failures

#### 1. The "Split-Brain Infrastructure & Unmanaged Network" Failure (Cascading Outage & Port Collisions)
- **What Happened**: Local developer environments, CI runners, and staging clusters independently mounted divergent Docker bridges without centralized network subnetting or port registries. Services spawned duplicate local Kafka brokers and Redis containers on default host ports (`5432`, `6379`, `9092`).
- **Impact**: Port collision conflicts (`EADDRINUSE`) routinely broke integration test pipelines and halted developer workflows. In multi-container polyglot integration environments, worker instances attached to disjoint bridge networks, creating partitioned split-brain states where half of the consumers consumed from local mock brokers while another set attempted connections to staging brokers. Critical budget exhaustion events were dropped silently, resulting in over $14,000 of runaway LLM API consumption before manual intervention.

#### 2. The "Over-Privileged Identity & Missing Network Firewall" Failure (Security & Data Exfiltration Risk)
- **What Happened**: Container workloads initially executed with default Linux root privileges (`UID 0`) and inherited broad cloud IAM roles (`Owner` or unconstrained compute admin roles). Within the cloud VPC, internal relational databases (`5432`), Redis instances (`6379`), and unauthenticated Kafka plaintext listeners (`9092`) resided in flat, shared subnets alongside public-facing REST endpoints without VPC firewall rules or private service access boundaries.
- **Impact**: Security vulnerability scanning revealed that an SSRF or Remote Code Execution vulnerability in any upstream API gateway could allow attackers to traverse the flat network, query the Google Cloud instance metadata server (`http://metadata.google.internal/computeMetadata/v1/`), harvest temporary access tokens, and exfiltrate unencrypted database credentials directly from memory.

#### 3. The "Stateful Crash & Silent Eviction" Failure (Missing Restart Policies & Ephemeral Storage)
- **What Happened**: Docker Compose manifests and early Kubernetes pod specs lacked automated container restart policies (`restart: "no"`) and omitted persistent volume mounts for stateful datastores (`google/alloydbomni`, `redis:7-alpine`, `confluentinc/cp-kafka`).
- **Impact**: During node memory pressure or system daemon updates, container engines terminated the database and Redis containers. The containers remained offline indefinitely. Upon manual restart, all ephemeral database tables and Redis rate-limiting keys were erased. The stateless alert workers crashed in retry loops against missing tables (`relation "alert_history" does not exist`). When the database was finally re-seeded, the loss of incident deduplication state triggered an alert storm—dispatching over 65,000 duplicate P1 pages and Slack messages within 8 minutes.

#### 4. The "Unchecked Infrastructure Drift & Deployment Lock-In" Failure (GitOps Sync Breakdown)
- **What Happened**: Kubernetes configurations, Helm values, and cloud Terraform modules drifted apart. Environment variables were manually injected into Kubernetes pods via `kubectl edit`, bypassing version control. Helm charts lacked standardized linting, packaging scripts, and semantic release automation.
- **Impact**: A production release failed during a live incident when newly introduced environment variables (`SERVICE_OWNERS_FILE_PATH`, `HEALTH_CHECK_PORT`) were missing in production ConfigMaps. Recovery took 52 minutes because the team lacked an automated rollback script (`deploy/release/rollback.sh`), causing complete telemetry blindness during a major external LLM provider outage.

---

## 2. Decision Outcome: The Declarative Multi-Target Architecture

To permanently resolve these failure modes, we adopted an immutable, multi-target deployment and infrastructure framework governed by the following core architectural decisions:

1. **Strict 10-Subsystem Package Layout & Hexagonal Isolation**:
   - `alert-engine` contains a dedicated, standardized `deploy/` directory housing:
     - `deploy/docker/`: Multi-stage builder/runner images (`service/Dockerfile`, `service/Dockerfile.dev`, `base/Dockerfile.base`) and standardized compose manifests (`single`, `polyglot`, `infra`).
     - `deploy/k8s/`: Production-grade Kubernetes base resources (`deployment`, `service`, `configmap`, `hpa`, `pdb`, `ingress`) and Kustomize overlays (`dev`, `staging`, `prod`, `local-polyglot`).
     - `deploy/helm/`: Packaged Helm charts with parameterized templates, OCI packaging scripts, and environment-specific values.
     - `deploy/argocd/`: Declarative GitOps AppProject and ApplicationSet definitions.
     - `deploy/terraform/`: Modular Google Cloud Platform Infrastructure as Code (IaC) managing Network, Security, Stateful datastores (AlloyDB, Memorystore Redis, Kafka), and Stateless compute.
     - `deploy/topology/`: Central `network_map.yaml` defining inter-service discovery, ports, and protocols.
     - `deploy/release/`: Automated, idempotently testable `deploy.sh` and `rollback.sh` runners.

2. **Decoupled Database-per-Service with Centralized Shared Infrastructure**:
   - **Centralized Infrastructure**: Kafka streaming buses (`llmobs-kafka:9092`), Redis spend ledgers (`llmobs-redis:6379`), and OpenTelemetry collectors (`llmobs-otel-collector:4318`) reside on the shared `llmobs-network` bridge.
   - **Service-Owned Datastores**: `alert-engine` exclusively owns its relational alert history database (`ewma_db` running on Google Cloud AlloyDB Omni / PostgreSQL). Direct cross-service database access is strictly prohibited.

3. **Multi-Subnet Network Segmentation & Zero-Trust Firewalling on Google Cloud**:
   - A dedicated Google Cloud VPC network (`${environment}-llmobs-vpc`) partitioned into:
     - **GKE Subnetwork (`10.0.1.0/24`)**: Private GKE worker nodes with secondary ranges for Pods (`10.48.0.0/14`) and Services (`10.52.0.0/20`), with Private Google Access enabled.
     - **Isolated Data Subnetwork (`10.0.11.0/24`)**: Non-routable private subnetwork hosting Kafka broker clusters and Private Service Access peering for AlloyDB and Memorystore Redis.
     - **Cloud NAT & Cloud Router**: Provides secure outbound egress for webhooks (Slack, PagerDuty) without exposing public IPs to worker nodes.
   - **Defense-in-Depth Cloud Firewalls**: Ingress firewall rules strictly permit health checks (`8001`) and metrics (`9464`) from the VPC/Pod CIDRs, restrict database access (`5432`, `6379`, `9092`) to tagged `alert-engine` instances, and enforce a default-deny priority 2000 rule against all external traffic to the data tier.

4. **Principle of Least Privilege Identity & Access Management (GCP IAM & Workload Identity)**:
   - Dedicated Google Service Account (`${environment}-alert-engine-sa`) bound to the GKE Kubernetes ServiceAccount via GKE Workload Identity (`roles/iam.workloadIdentityUser`).
   - Scoped IAM roles granting read-only access to Google Cloud Secret Manager (`roles/secretmanager.secretAccessor`) and Google Cloud KMS (`roles/cloudkms.cryptoKeyDecrypter`) with automatic 30-day key rotation.

5. **Deterministic State Recovery & High-Availability Resilience**:
   - Containers declare `restart: unless-stopped` with named persistent storage volumes (`alert_engine_alloydb_data`, `llmobs_kafka_data`, `llmobs_redis_data`).
   - Pod Disruption Budgets (`minAvailable: 1`) and Horizontal Pod Autoscaling (CPU 75%, Memory 80%) guarantee high availability during cluster maintenance or traffic surges.

---

## 3. High Level Design (HLD) & Infrastructure Topology

### 3.1 Google Cloud Platform (GCP) Infrastructure Topology Diagram

```mermaid
flowchart TD
    Internet([Internet / External Alert Sinks]) --> CloudNAT[Google Cloud NAT / Cloud Router]

    subgraph GCP_Project["Google Cloud Project (llmobs-${environment})"]
        subgraph VPC["VPC Network: ${environment}-llmobs-vpc"]
            
            subgraph GKE_Tier["Private GKE Node Pool Subnet (10.0.1.0/24)"]
                direction TB
                GkeIngress[Internal Ingress / GKE Service] --> AlertPod1["alert-engine Pod 1\n(:8001 Health / :9464 Metrics)\nTags: alert-engine"]
                GkeIngress --> AlertPod2["alert-engine Pod 2\n(:8001 Health / :9464 Metrics)\nTags: alert-engine"]
                GkeHPA["Horizontal Pod Autoscaler (HPA)\nMin: 2, Max: 8"] -.->|Auto-scales| AlertPod1
                GkePDB["Pod Disruption Budget (PDB)\nminAvailable: 1"] -.->|Protects| AlertPod1
                CloudNAT -->|Egress Webhook Calls| AlertPod1
            end

            subgraph Data_Tier["Private Service Access / Data Subnet (10.0.11.0/24)"]
                direction TB
                GCP_AlloyDB[("Google Cloud AlloyDB Cluster\nPrimary Instance (2 vCPU)\nDatabase: ewma_db\nPrivate IP: 10.x.x.x")]
                GCP_Redis[("Google Cloud Memorystore Redis 7\nAuth Enabled / Private Access\nPort: 6379")]
                GCP_Kafka["Kafka Broker Cluster\nManaged Instance Group (3 Nodes)\nPorts: 9092, 9093\nTags: data-tier, kafka-broker"]
            end

            subgraph Firewall_Rules["GCP VPC Firewall Policy Rules"]
                FW_Health["Rule: allow-health-metrics\nIngress TCP 8001, 9464 from Pods"]
                FW_Data["Rule: allow-data-access\nIngress TCP 5432, 6379, 9092 strictly from tag:alert-engine"]
                FW_Deny["Rule: deny-external-data\nPriority 2000 Deny 0.0.0.0/0 to tag:data-tier"]
            end
        end

        subgraph SecurityPlane["GCP Security & Identity Plane"]
            GCP_SA["Google Service Account\nalert-engine-sa@project.iam.gserviceaccount.com"]
            GCP_WI["Workload Identity Binding\nroles/iam.workloadIdentityUser\nBound to k8s SA: alert-engine"]
            GCP_KMS["Google Cloud KMS KeyRing\nCryptoKey: alert-engine-key\n(30-day auto-rotation)"]
            GCP_Secrets["Google Secret Manager\nSecret: ${env}-alert-engine-database\n(username, password, db)"]
            GCP_GCS[("Cloud Storage (GCS)\n${project}-${env}-alert-engine-artifacts\nUniform Bucket Access / Versioning")]
            
            GCP_SA --> GCP_KMS
            GCP_SA --> GCP_Secrets
            GCP_SA --> GCP_GCS
            AlertPod1 -.->|"Workload Identity"| GCP_SA
        end
    end

    subgraph ExternalEgress["External Incident Sinks"]
        Slack["Slack Incoming Webhooks"]
        PagerDuty["PagerDuty Events v2 API"]
    end

    AlertPod1 -->|"Consume Events (Offset Commit)"| GCP_Kafka
    AlertPod1 -->|"Atomic Rate Limiting"| GCP_Redis
    AlertPod1 -->|"Audit Trail Persistence"| GCP_AlloyDB
    AlertPod1 -->|"Dispatches Webhooks (via Cloud NAT)"| Slack
    AlertPod1 -->|"P1 Escalation (via Cloud NAT)"| PagerDuty
```

---

## 4. Deep-Dive Infrastructure Subsystems

### 4.1 Network Infrastructure: GCP VPC, Subnetworks, and Cloud NAT

The network topology implements multi-zone resilience and private-only addressing across Google Cloud:

```mermaid
flowchart LR
    subgraph VPC_Network["Google Cloud VPC Network: ${environment}-llmobs-vpc"]
        subgraph Subnet_GKE["Subnetwork: gke-subnet (10.0.1.0/24)"]
            Primary_Range["Node IPs: 10.0.1.0/24"]
            Secondary_Pods["Secondary Range 'gke-pods': 10.48.0.0/14"]
            Secondary_Services["Secondary Range 'gke-services': 10.52.0.0/20"]
        end

        subgraph Subnet_Data["Subnetwork: data-subnet (10.0.11.0/24)"]
            Kafka_Nodes["Compute Engine Kafka MIG\n10.0.11.x (3 Nodes)"]
            PGA["Private Google Access: ENABLED"]
        end

        subgraph PSA_Range["Private Service Access (VPC Peering: 10.16.0.0/16)"]
            AlloyDB_Private["Google Cloud AlloyDB Omni Instance\nInternal IP Peered"]
            Redis_Private["Cloud Memorystore Redis 7\nInternal IP Peered"]
        end
    end

    Router["Cloud Router: nat-router"] --> NAT_GW["Cloud NAT: nat-gw (AUTO_ONLY IPs)"]
    Subnet_GKE -->|"Private Outbound 0.0.0.0/0"| NAT_GW
    NAT_GW -->|"Egress to Slack / PagerDuty"| ExtInternet[Public Internet]
```

#### Detailed Google Cloud Subnetwork Allocation Table
| Subnetwork Name | Primary CIDR Block | Secondary CIDR Ranges | Private Google Access | Purpose & Placed Workloads |
|---|---|---|---|---|
| `${environment}-gke-subnet` | `10.0.1.0/24` | `gke-pods`: `10.48.0.0/14`<br>`gke-services`: `10.52.0.0/20` | Enabled | GKE worker nodes executing `alert-engine` replicas |
| `${environment}-data-subnet` | `10.0.11.0/24` | None | Enabled | Kafka Managed Instance Group (MIG) brokers |
| `servicenetworking-peering` | `10.16.0.0/16` | Allocated Global Range | N/A (Internal Peering) | Google Cloud AlloyDB cluster and Memorystore Redis |

---

### 4.2 Security & Firewall Infrastructure: GCP Workload Identity & Cloud Firewalls

```mermaid
flowchart TD
    subgraph TrafficFlow["GCP Inbound and Identity Security Pipeline"]
        Packet["Incoming Ingress Packet"] --> FW1{"1. GCP VPC Firewall Filter"}
        FW1 -->|Port 8001 and 9464 Allowed| GKE_Node["2. GKE Node and Container Runtime (Non-Root UID 10001)"]
        FW1 -->|"Port 5432, 6379, 9092 Allowed from Tag alert-engine"| Data_Node["Data Tier Services"]
        FW1 -->|"Rule Deny Priority 2000"| Drop["Dropped Packet (FW Denied)"]
        
        GKE_Node --> WI_Auth{"3. GKE Workload Identity"}
        WI_Auth -->|Assume Service Account| GCP_Token["GCP Short-Lived Access Token"]
        GCP_Token --> DecryptSecret["4. Secret Manager and KMS Decryption"]
        DecryptSecret --> SecureBoot["5. Secure Engine Boot and Execution"]
    end
```

#### GCP Firewall Rules Matrix
| Firewall Rule Name | Direction | Protocol | Port Range | Source Target | Destination Target | Security Purpose |
|---|---|---|---|---|---|---|
| `allow-health-metrics` | Ingress | TCP | `8001`, `9464` | `10.0.0.0/16`, `10.48.0.0/14` | Target tag: `alert-engine` | Allows kubelet liveness/readiness probes and Prometheus scraping |
| `allow-data-access` | Ingress | TCP | `5432`, `6379`, `9092-9094` | Source tag: `alert-engine` | Target tag: `data-tier` | Strictly restricts database and Kafka access to alert-engine pods |
| `deny-external-data` | Ingress | ALL | ALL | `0.0.0.0/0` | Target tag: `data-tier` (Priority 2000) | Complete isolation of databases from any external inbound traffic |

---

### 4.3 Storage Infrastructure: AlloyDB Omni, Cloud Memorystore, and GCS

```mermaid
flowchart TD
    subgraph StreamingPlane["1. Event Streaming Ledger (Kafka MIG)"]
        TopicBudget["alerts.budget\n(Compacted / 7 Days)"]
        TopicCost["alerts.cost.anomaly\n(Retained 14 Days)"]
        TopicTox["llm.toxicity.flagged\n(Encrypted / 30 Days)"]
        TopicSlo["alerts.latency.slo\n(Retained 7 Days)"]
    end

    subgraph MemoryTier["2. Real-Time Distributed Ledger (Cloud Memorystore Redis 7)"]
        RateLimits["Sliding Window Rate Limiters\n(Key: alert_rl:{tenant}:{type})"]
        IncidentState["Incident Lifecycle Tracker\n(Key: alert_inc:{service}:{incident_id})"]
        DedupIndex["Fingerprint Deduplication Cache\n(Key: alert_dedup:{sha256_hash})"]
    end

    subgraph RelationalStore["3. Audit & State Store (Google Cloud AlloyDB Omni)"]
        TableAlerts["Table: alert_history\n- alert_id (UUID, PK)\n- alert_type (Enum)\n- severity (Enum)\n- tenant_id (VARCHAR)\n- payload (JSONB)\n- created_at (TIMESTAMPTZ)"]
        TableAudits["Table: alert_dispatch_logs\n- dispatch_id (UUID)\n- target_sink (Slack/PD)\n- status_code (INT)\n- latency_ms (NUMERIC)"]
    end

    subgraph ObjectStore["4. Cloud Storage Archive (Google Cloud Storage)"]
        ArtifactBucket["GCS Bucket: ${project}-${env}-alert-engine-artifacts\n- Uniform Bucket-Level Access\n- Object Versioning Enabled\n- Google-Managed / KMS Customer Encryption"]
    end

    StreamingPlane -->|"Poll & Commit Offsets"| Worker["alert-engine Consumer"]
    Worker -->|"HINCRBY / Sliding Window Query"| MemoryTier
    Worker -->|"INSERT ON CONFLICT"| RelationalStore
    Worker -.->|"Flush Diagnostic Dumps"| ObjectStore
```

---

### 4.4 Service & Messaging Infrastructure: Topic Contracts & Polyglot Integration

`alert-engine` communicates across the monorepo using versioned asynchronous contracts registered in `messaging/schemas/`:

```mermaid
flowchart TD
    subgraph SiblingServices["Monorepo Sibling Producers (Polyglot Sub-Packages)"]
        direction TB
        BudgetService["budget-provisioner\n(Go / Python)"]
        CostService["event-cost\n(Python Daemon)"]
        ToxicityService["toxicity\n(Rust / Python)"]
        QualityService["quality-engine\n(Python ML)"]
        LatencyService["latency-engine\n(Go / Python)"]
        SloService["slo-burn-worker\n(Python Engine)"]
    end

    subgraph KafkaBroker["Central Kafka Streaming Plane (llmobs-kafka:9092)"]
        direction TB
        subgraph TopicBudget["Topic: alerts.budget"]
            SchemaBudget["Contract: messaging/schemas/alerts.budget.yaml\n- tenant_id (string)\n- budget_limit (float)\n- current_spend (float)\n- currency (string)"]
        end

        subgraph TopicCost["Topic: alerts.cost.anomaly"]
            SchemaCost["Contract: messaging/schemas/alerts.cost.anomaly.yaml\n- tenant_id (string)\n- metric (string)\n- current_spend (float)\n- window_mean (float)\n- sigma_threshold (float)"]
        end

        subgraph TopicTox["Topic: llm.toxicity.flagged"]
            SchemaTox["Contract: messaging/schemas/llm.toxicity.flagged.yaml\n- prompt_id (string)\n- toxicity_score (float)\n- flagged_categories (list)\n- model (string)"]
        end

        subgraph TopicQuality["Topic: alerts.quality.degradation"]
            SchemaQuality["Contract: messaging/schemas/alerts.quality.degradation.yaml\n- model (string)\n- degradation_score (float)\n- threshold (float)\n- baseline_score (float)"]
        end

        subgraph TopicLatency["Topic: alerts.latency.slo"]
            SchemaLatency["Contract: messaging/schemas/alerts.latency.slo.yaml\n- endpoint (string)\n- slo_target_ms (float)\n- current_p95_ms (float)\n- sample_count (int)"]
        end

        subgraph TopicTtft["Topic: alerts.latency.ttft_regression"]
            SchemaTtft["Contract: messaging/schemas/alerts.latency.ttft_regression.yaml\n- provider (string)\n- baseline_ttft_ms (float)\n- current_ttft_ms (float)\n- delta_percentage (float)"]
        end
    end

    subgraph AlertEngineConsumer["alert-engine Consumer Pipeline (alert-engine-group)"]
        direction TB
        Dispatcher["Central Event Dispatcher & Envelope Builder\n(messaging/engine/consumers/dispatcher.py)"]
        
        subgraph Handlers["Feature Handlers & Invariant Rules"]
            H_Budget["AlertsBudgetHandler\n(src/handlers/alerts_budget/)"]
            H_Cost["AlertsCostAnomalyHandler\n(src/handlers/alerts_cost_anomaly/)"]
            H_Tox["AlertsToxicityHandler\n(src/handlers/alerts_toxicity/)"]
            H_Quality["AlertsQualityDegradationHandler\n(src/handlers/alerts_quality_degradation/)"]
            H_Slo["AlertsLatencySloHandler\n(src/handlers/alerts_latency_slo/)"]
            H_Ttft["AlertsLatencyTtftRegressionHandler\n(src/handlers/alerts_latency_ttft_regression/)"]
        end

        RateLimiter["Redis Sliding Window Rate Limiter & Deduplicator\n(src/shared/utils/rate_limiter.py)"]
        OwnerResolver["Service Owners Registry Resolver\n(config/service_owners.yaml)"]
        DeadLetterQueue["Dead Letter Pipeline Router (DLQ)\n(messaging/engine/pipeline/dead_letter_router.py)"]
    end

    subgraph Sinks["Operational Notification Sinks & Storage Plane"]
        SlackChannel["Slack Webhook\n(#alerts / #security / #eng)"]
        PagerDutyAlert["PagerDuty Events v2\n(P1/Critical Incidents)"]
        AuditDB[("PostgreSQL / AlloyDB\nTable: alert_history")]
        DLQTopic[("Kafka DLQ Topic\nalerts.dead_letter_queue")]
    end

    %% Event Ingestion
    BudgetService -->|"Publishes CloudEvent"| TopicBudget
    CostService -->|"Publishes CloudEvent"| TopicCost
    ToxicityService -->|"Publishes CloudEvent"| TopicTox
    QualityService -->|"Publishes CloudEvent"| TopicQuality
    LatencyService -->|"Publishes CloudEvent"| TopicLatency
    SloService -->|"Publishes CloudEvent"| TopicTtft

    %% Consumption to Dispatcher
    TopicBudget -->|"Poll (Offset Commit)"| Dispatcher
    TopicCost -->|"Poll (Offset Commit)"| Dispatcher
    TopicTox -->|"Poll (Offset Commit)"| Dispatcher
    TopicQuality -->|"Poll (Offset Commit)"| Dispatcher
    TopicLatency -->|"Poll (Offset Commit)"| Dispatcher
    TopicTtft -->|"Poll (Offset Commit)"| Dispatcher

    %% Dispatcher to Handlers
    Dispatcher -->|"Route: alerts.budget"| H_Budget
    Dispatcher -->|"Route: alerts.cost.anomaly"| H_Cost
    Dispatcher -->|"Route: llm.toxicity.flagged"| H_Tox
    Dispatcher -->|"Route: alerts.quality.degradation"| H_Quality
    Dispatcher -->|"Route: alerts.latency.slo"| H_Slo
    Dispatcher -->|"Route: alerts.latency.ttft_regression"| H_Ttft
    Dispatcher -.->|"Malformed JSON / Schema Error"| DeadLetterQueue

    %% Handlers to Shared Components
    H_Budget --> RateLimiter
    H_Cost --> RateLimiter
    H_Tox --> RateLimiter
    H_Quality --> RateLimiter
    H_Slo --> RateLimiter
    H_Ttft --> RateLimiter

    RateLimiter -->|"Allowed"| OwnerResolver
    RateLimiter -.->|"Rate Limited (Suppressed)"| AuditDB

    OwnerResolver -->|"Channel & Mention"| SlackChannel
    OwnerResolver -->|"P1 Escalation Key"| PagerDutyAlert
    OwnerResolver -->|"Audit Trail"| AuditDB
    DeadLetterQueue -->|"Poison Pill Storage"| DLQTopic
```

---

## 5. Low Level Design (LLD): Execution Flows & Decision Trees

### 5.1 End-to-End Functional Call Stack: Message Ingestion to Notification Dispatch

The execution flow traverses from the low-level Kafka consumer socket up through the deserialization layer, domain workflows, rate-limiting guards, and outbound HTTP dispatch adapters:

```
[Operating System & Network Wire]
 1. Kernel TCP Socket receives packet from Kafka Broker (Port 9092)
      │
      ▼
 2. confluent_kafka.Consumer.poll(timeout=1.0) returns ConsumerRecord
      │
      ▼
[Messaging & Ingress Layer]
 3. alert_engine.worker.index.run_worker_loop()
      │
      ▼
 4. alert_engine.main._extract_traceparent(msg.headers()) [Extracts W3C traceparent]
      │
      ▼
 5. opentelemetry.trace.Tracer.start_as_current_span("alert_engine.consume_message")
      │
      ▼
 6. json.loads(msg.value()) -> deserializes JSON envelope
      │
      ▼
[Dispatcher & Routing Layer]
 7. alert_engine.worker.registry.HandlerRegistry.dispatch(topic, payload)
      │
      ▼
 8. Specific Feature Handler invoked:
    - AlertsBudgetHandler.handle(payload)
    - AlertsCostAnomalyHandler.handle(payload)
    - AlertsToxicityHandler.handle(payload)
    - AlertsQualityDegradationHandler.handle(payload)
    - AlertsLatencySloHandler.handle(payload)
    - AlertsLatencyTtftRegressionHandler.handle(payload)
      │
      ▼
[Domain Rules & Invariants Evaluation]
 9. FeatureRules.evaluate(event_payload)
      │
      ├── IF invariant violated (e.g. current_spend >= budget_limit):
      │     proceed to Step 10
      └── ELSE:
            Drop event as non-actionable; record metric and exit cleanly
      │
      ▼
[Resilience & Rate Limiting Step]
10. RedisRateLimiter.is_rate_limited(key=f"alert:{tenant_id}:{alert_type}", max_events=10, window_seconds=60)
      │
      ├── IF Rate Limited:
      │     Record metric 'alert_rate_limited_suppressed'; skip external webhooks; proceed to persistence
      └── ELSE:
            Acquire rate limit token; proceed to notification dispatch
      │
      ▼
[Service Ownership Resolution]
11. ServiceOwnersResolver.resolve_owner(service_name)
      - Reads cached configuration from config/service_owners.yaml
      - Injects Slack channel handle (e.g. "@platform-oncall") and PagerDuty routing key
      │
      ▼
[Outbound Notification Dispatch (Hexagonal Adapters)]
12. SlackAdapter.send_notification(channel, message, blocks)
      - Formats Slack Block Kit JSON
      - Dispatches HTTP POST to Slack Webhook via httpx.Client
      │
13. PagerDutyAdapter.trigger_incident(routing_key, severity, summary, dedup_key)
      - Formats PagerDuty Events API v2 payload
      - Dispatches HTTP POST to https://events.pagerduty.com/v2/enqueue
      │
      ▼
[Persistence & Audit Trail]
14. PostgresAdapter.insert_alert(alert_record)
      - Acquires database connection from connection pool
      - Executes: INSERT INTO alert_history (alert_id, alert_type, severity, tenant_id, payload, created_at)
      - Maps relational constraint violations via DbErrorMapping
      │
      ▼
[Kafka Commit & Span Completion]
15. confluent_kafka.Consumer.commit(message=msg, asynchronous=True)
16. Span.set_status(Status(StatusCode.OK)) -> OpenTelemetry span ends
```

---

### 5.2 Internal Pipeline Decision Tree: Exhaustive IF/ELSE Execution Logic

```text
+------------------------------------------------------------------------------------------------------------------------+
|                                ALERT ENGINE DISPATCH & INFRASTRUCTURE DECISION TREE                                    |
|                      (All Failure Paths, Rate Limiters, State Checks, and Fallbacks Covered)                           |
+------------------------------------------------------------------------------------------------------------------------+

[KAFKA MESSAGE INGESTION] -> ConsumerRecord(topic, partition, offset, key, value, headers)
   │
   +--> STEP 1: Message Validation & Deserialization
   |      |
   |      +-- IF (msg is None OR msg.error() is not None):
   |      |     |-- [LOG WARN] "Kafka consumer poll returned error or EOF"
   |      |     +-- [RETURN] Await next poll cycle (No offset commit)
   |      |
   |      +-- TRY:
   |      |     parsed_payload = json.loads(msg.value().decode("utf-8"))
   |      |   EXCEPT json.JSONDecodeError:
   |      |     |-- [LOG CRITICAL] "Malformed JSON payload. Routing to Dead Letter Queue (DLQ)"
   |      |     |-- [EMIT] Kafka DLQ Producer -> 'alerts.dlq'
   |      |     +-- [COMMIT] Commit offset to prevent poison pill loop
   |      |
   |      +-- [PASS] Payload valid JSON. Proceed to Step 2.
   |
   +--> STEP 2: Topic Routing & Handler Dispatch
   |      |
   |      +-- handler = HandlerRegistry.get(msg.topic())
   |      +-- IF (handler is None):
   |      |     |-- [LOG ERROR] "Unregistered Kafka topic: " + msg.topic()
   |      |     +-- [COMMIT] Commit offset; drop unroutable message
   |      |
   |      +-- [PASS] Handler resolved. Proceed to Step 3.
   |
   +--> STEP 3: Business Invariant Evaluation
   |      |
   |      +-- IF (topic == "alerts.budget"):
   |      |     +-- IF (payload.current_spend < payload.budget_limit * 0.8):
   |      |     |     |-- [LOG DEBUG] "Budget spend below warning threshold (80%). Suppressed."
   |      |     |     +-- [SKIP] Do not notify
   |      |     +-- ELSE IF (payload.current_spend >= payload.budget_limit):
   |      |     |     |-- severity = "CRITICAL"
   |      |     |     +-- action = "BLOCK_AND_PAGE"
   |      |     +-- ELSE:
   |      |           |-- severity = "WARNING"
   |      |           +-- action = "NOTIFY_SLACK"
   |      |
   |      +-- ELSE IF (topic == "llm.toxicity.flagged"):
   |      |     +-- IF (payload.toxicity_score < 0.85):
   |      |     |     +-- [SKIP] Toxicity below critical flag threshold
   |      |     +-- ELSE:
   |      |           |-- severity = "CRITICAL"
   |      |           +-- action = "PAGE_SAFETY_TEAM"
   |      |
   |      +-- ELSE:
   |            +-- [EVALUATE] Run domain-specific threshold logic
   |
   +--> STEP 4: Distributed Rate Limiting & Incident Deduplication (Redis)
   |      |
   |      +-- dedup_key = sha256(f"{tenant_id}:{alert_type}:{service_name}")
   |      +-- is_active_incident = redis.get(f"incident:{dedup_key}")
   |      |
   |      +-- IF (is_active_incident is not None AND is_active_incident == "ACKNOWLEDGED"):
   |      |     |-- [LOG INFO] "Active incident already acknowledged by on-call. Suppressing notifications."
   |      |     +-- [SKIP NOTIFICATION] Proceed to persistence
   |      |
   |      +-- rate_limit_allowed = redis.acquire_rate_limit(key=f"rl:{dedup_key}", max=5, window=300)
   |      +-- IF (rate_limit_allowed == False):
   |      |     |-- [LOG WARN] "Notification rate limit saturated (5 alerts/5m). Throttling notification."
   |      |     |-- [METRIC] Increment 'alert_engine.notifications_rate_limited'
   |      |     +-- [SKIP NOTIFICATION] Proceed to persistence
   |      |
   |      +-- [PASS] Notification permitted. Proceed to Step 5.
   |
   +--> STEP 5: Notification Dispatch (Slack & PagerDuty)
   |      |
   |      +-- IF (severity in ["CRITICAL", "P1"]):
   |      |     +-- TRY:
   |      |     |     incident_id = pagerduty.trigger_incident(dedup_key, summary, severity)
   |      |     |     redis.setex(f"incident:{dedup_key}", 14400, "TRIGGERED")
   |      |     |   EXCEPT PagerDutyApiError as e:
   |      |     |     |-- [LOG CRITICAL] "PagerDuty dispatch failed: " + str(e)
   |      |     |     +-- [FALLBACK] Force emergency Slack broadcast to #incident-war-room
   |      |
   |      +-- TRY:
   |      |     slack.send_message(channel=owner_channel, text=alert_summary)
   |      |   EXCEPT SlackWebhookError as e:
   |      |     |-- [LOG WARN] "Slack webhook delivery failed: " + str(e)
   |      |     +-- [RETRY] Push to memory retry queue (max 3 retries)
   |      |
   |      +-- [PASS] Notifications dispatched. Proceed to Step 6.
   |
   +--> STEP 6: Relational Audit Trail Persistence (AlloyDB / Postgres)
   |      |
   |      +-- TRY:
   |      |     postgres_adapter.insert_alert(alert_record)
   |      |   EXCEPT DatabaseConstraintError as e:
   |      |     |-- [LOG ERROR] "Database constraint violation: " + str(e)
   |      |     +-- [HANDLE] Duplicate alert ID safely ignored
   |      |   EXCEPT DatabaseConnectionError as e:
   |      |     |-- [LOG CRITICAL] "Database connection pool saturated or offline: " + str(e)
   |      |     +-- [FAILOVER] Write emergency JSON audit log to local container disk
   |      |
   |      +-- [PASS] Audit recorded. Proceed to Step 7.
   |
   +--> STEP 7: Offset Commit & Telemetry Completion
          |
          +-- kafka_consumer.commit(asynchronous=True)
          +-- span.set_attribute("alert.processed", True)
          +-- [COMPLETED] Loop advances to next message
```

---

## 6. Failure-First Matrix: Comprehensive Failure Modes & Defenses

| Failure Mode ID | Component | Root Cause / Trigger | Failure Symptoms & Blast Radius | Detection Mechanism & Metric Threshold | Automated Recovery & Resilience Strategy |
|---|---|---|---|---|---|
| **FM-INFRA-001** | Kafka Streaming Bus | Broker node crash, network partition, or topic rebalance stall | Consumers hang; alert messages queue up; latency alerts delayed | `kafka_consumer_group_lag > 500` messages; Prometheus alert fires within 60s | Multi-node MSK broker topology across 3 AZs; client auto-reconnects with exponential backoff |
| **FM-INFRA-002** | AlloyDB Omni / Postgres | Disk exhaustion, deadlocks, connection pool saturation | `DbExecutionError` raised; alert history cannot be written | Connection wait duration `> 2.0s`; pool active count `= max_connections` | Connection pool backoff; transient retries; errors routed to fallback logging without crashing consumer thread |
| **FM-INFRA-003** | Redis Ledger & Cache | OOM eviction, network timeout, node failover | `RedisStorageError`; sliding rate limits cannot be queried | Redis ping response latency `> 100ms`; failed ping health checks | Sentinel/ElastiCache automatic node promotion; fail-open rate limiting to avoid dropping critical P1 safety alerts |
| **FM-INFRA-004** | Outbound Webhook (Slack) | Slack HTTP 429 rate limit or HTTP 500/503 outage | Slack notification drop; engineers not alerted in channels | `alert_delivery_failure_total{sink="slack"} > 10` in 5m | Circuit breaker trips; failed notifications queued in local memory/DLQ; fallback to PagerDuty for critical severity |
| **FM-INFRA-005** | PagerDuty API | Invalid routing key, PagerDuty network timeout | P1 incident fails to trigger on-call escalation | `alert_delivery_failure_total{sink="pagerduty"} > 0` | Immediate retry with jittered exponential backoff; fallback emergency log emission to Datadog/CloudWatch |
| **FM-INFRA-006** | Kubernetes Worker Pod | Memory leak, unhandled exception, OOM kill | Container terminates unexpectedly; pod restarts | Container restart count `> 3` in 15m; Kubernetes `OOMKilled` event | Pod Disruption Budget guarantees minimum 1 pod online; Kubernetes restarts container; state restored from Kafka offsets |
| **FM-INFRA-007** | Network Ingress / NACL | Misconfigured firewall rule, security group drift | Health check probes fail; ingress controller returns 502/504 | K8s liveness probe failure count `>= 3`; pod marked Unhealthy | Declarative Terraform state management; CI runs `terraform validate` to detect configuration errors prior to deployment |
| **FM-INFRA-008** | GitOps Sync Engine | Invalid YAML syntax, missing image tag in registry | ArgoCD sync fails; release blocked | ArgoCD `SyncStatus = OutOfSync` or `HealthStatus = Degraded` | Automated rollback script (`deploy/release/rollback.sh`) reverts to previous healthy Git commit |
| **FM-INFRA-009** | Cloud KMS / IAM Token | STS token expiration, KMS key deletion/disabling | Pod unable to decrypt database credentials on boot | AWS STS AssumeRole failure rate `> 0`; pod crashloop in init phase | Kubernetes ServiceAccount token auto-refreshed; KMS key protected by `deletion_window_in_days = 30` |
| **FM-INFRA-010** | NAT Gateway Schedulers | NAT Gateway IP exhaustion or AWS AZ failure | Outbound HTTP calls to Slack/PagerDuty hang and time out | TCP SYN drop count `> 50`; NAT Gateway packet drop metric | Multi-AZ NAT Gateway failover; connection pools enforce aggressive 5s connect timeouts |

---

## 7. Review Trigger & Reversal Criteria

This architectural decision MUST be formally re-evaluated if:
1. Message throughput across the 6 alert topics exceeds **50,000 messages/second**, necessitating distributed streaming architectures (e.g. Apache Flink) in place of direct Python consumers.
2. Cross-region or multi-cloud deployment requirements arise, requiring geo-replicated AlloyDB clusters and global service meshes (Istio/Linkerd).
3. Database storage requirements exceed single-node AlloyDB vertical scaling limits, requiring migration to distributed columnar analytics (ClickHouse) for long-term alert retention.
4. Total egress webhook traffic exceeds external Slack API quotas (1 message/sec per channel), necessitating an asynchronous notification aggregation and digest pipeline.
