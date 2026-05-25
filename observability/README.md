# Observability Setup Guide

This directory contains everything needed to enable **Live Agent Observability & Business Dashboards** for the Mall Operations Brain.

---

## Quick Start

### 1. Get Your Elastic APM Credentials

In your Elastic Cloud Serverless deployment:

1. Open **Kibana → Observability → APM → Add data**
2. Select **OpenTelemetry**
3. Copy the **OTLP endpoint URL** and **secret token**

### 2. Configure Environment

Add these variables to `backend/.env`:

```bash
# ── Elastic APM / OpenTelemetry ──
OTEL_EXPORTER_OTLP_ENDPOINT=https://your-deployment.apm.us-central1.gcp.elastic.cloud:443
OTEL_EXPORTER_OTLP_HEADERS="Authorization=Bearer your_apm_secret_token"
OTEL_SERVICE_NAME=mall-operations-brain
```

> **No endpoint configured?** The backend falls back to **console exporters** automatically — traces and metrics are printed to stdout for local development.

### 3. Install Updated Dependencies

```bash
make install
```

This installs the new OTel packages:
- `opentelemetry-api`
- `opentelemetry-sdk`
- `opentelemetry-instrumentation-fastapi`
- `opentelemetry-exporter-otlp-proto-http`

### 4. Build the Dashboard Native in Kibana

Because Kibana's internal Lens JSON schema changes rapidly, importing hand-rolled dashboard JSONs can cause UI crashes (like the `.map()` undefined error). 

Instead, building the dashboard takes just a few minutes using Kibana's native UI and **ES|QL**.

1. Open **Kibana → Analytics → Dashboards** and click **Create dashboard**
2. For each panel below, click **Create visualization** and use the **ES|QL** tab.

---

## Dashboard Layout & Queries

The dashboard should be split into two hemispheres:

### 🤖 Agent Health (Left Side)

**1. ES|QL Query Volume** (Area Chart)
```esql
FROM metrics-* 
| WHERE metricset.name == "agent.esql.queries"
| STATS query_count = SUM(agent.esql.queries) BY status
| KEEP @timestamp, status, query_count
```
*(Select Area chart, X-axis: `@timestamp`, Y-axis: `query_count`, Break down by: `status`)*

**2. Tool Success Rate** (Donut Chart)
```esql
FROM metrics-*
| WHERE metricset.name == "agent.tool.calls"
| STATS call_count = SUM(agent.tool.calls) BY status
```
*(Select Donut chart, Slice by: `status`, Size by: `call_count`)*

**3. Token Burn Rate** (Line Chart)
```esql
FROM metrics-*
| WHERE metricset.name == "agent.tokens.consumed"
| STATS tokens = SUM(agent.tokens.consumed) BY agent_name
| KEEP @timestamp, agent_name, tokens
```
*(Select Line chart, X-axis: `@timestamp`, Y-axis: `tokens`, Break down by: `agent_name`)*

### 🏬 Business Impact (Right Side)

**1. AI-Driven Conversions** (Metric)
```esql
FROM metrics-*
| WHERE metricset.name == "coupon.activations"
| STATS total_activations = SUM(coupon.activations)
```
*(Select Metric visualization, Field: `total_activations`)*

**2. Activation Method Distribution** (Pie Chart)
```esql
FROM metrics-*
| WHERE metricset.name == "coupon.activations"
| STATS activations = SUM(coupon.activations) BY method
```
*(Select Pie chart, Slice by: `method`, Size by: `activations`)*

**3. Autonomous Pulse Runs** (Bar Chart)
```esql
FROM metrics-*
| WHERE metricset.name == "pulse.workflow.runs"
| STATS runs = SUM(pulse.workflow.runs) BY source
| KEEP @timestamp, source, runs
```
*(Select Bar chart, X-axis: `@timestamp`, Y-axis: `runs`, Break down by: `source`)*

---

## Metrics Reference

All custom metrics are now actively emitting to your Elasticsearch `metrics-*` data streams via APM:

| Metric | Type | Attributes | Source |
|--------|------|------------|--------|
| `agent.tokens.consumed` | Counter | `role`, `agent_name` | `main.py` — session finalization |
| `agent.tool.calls` | Counter | `tool_name`, `status` | `main.py` — tool response handler |
| `agent.reasoning.duration_ms` | Histogram | `role`, `agent_name` | `main.py` — time between events |
| `agent.tool.duration_ms` | Histogram | `tool_name`, `status` | `main.py` — tool call→response delta |
| `agent.esql.queries` | Counter | `status` | `tools.py` — `_execute_esql()` |
| `agent.sessions.total` | Counter | `role`, `agent_name` | `main.py` — session creation |
| `coupon.activations` | Counter | `store_name`, `method` | `tools.py` — `activate_customer_coupon()` |
| `pulse.workflow.runs` | Counter | `source` | `main.py` — `get_pulse_feed()` |
| `search.hybrid.queries` | Counter | `floor` | `main.py` — `hybrid_search()` |

## Trace Spans

| Span Name | Parent | Key Attributes |
|-----------|--------|---------------|
| `agent.session` | Root | `role`, `agent_name`, `session_id`, `user_message`, `tool_call_count`, `reasoning_steps`, `estimated_tokens` |
| `esql.query` | Tool execution | `esql.query`, `esql.row_count`, `esql.column_count` |
| `coupon.activation` | Tool execution | `store_name`, `shopper_id`, `method`, `token`, `duration_ms` |
| `pathfinder.calculate` | Tool execution | `stop_count`, `start_zone` |
| `search.hybrid` | HTTP request | `search.query`, `search.floor_filter` |
| `pulse.feed.fetch` | HTTP request | `pulse.index`, `pulse.source`, `pulse.card_count` |
