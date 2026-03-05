# Processors Design — LoanFlow AI

This document describes what currently exists for background processing in this repository.

## Current State

- A processor application exists at `py/apps/processors/`.
- The app entrypoint is `py/apps/processors/processor.py`.
- Current root Terraform (`infra/main.tf`) does not deploy a Service Bus + KEDA queue-processing pipeline.

## Purpose

The processors app is a place for asynchronous/background workloads that should not block the API request path. In LoanFlow AI that includes potential future work such as:

- document post-processing,
- asynchronous verification/enrichment,
- downstream integration handoffs,
- scheduled compliance/operations jobs.

## Design Direction

When introducing a processor workflow in this repo, keep these constraints:

1. Reuse existing observability conventions (`structlog`, OpenTelemetry).
2. Keep backend request latency isolated from background work.
3. Prefer idempotent writes in Cosmos-backed flows.
4. Keep deployment wiring explicit in `infra/` before enabling production traffic.

## Local Development

For local experiments, run the processor directly from `py/apps/processors` and configure required environment variables via local `.env` patterns.

## Migration Note

Older docs referred to a Contoso-specific handoff queue architecture. That architecture is not the active implementation for LoanFlow AI and should not be treated as source of truth for this repo.
