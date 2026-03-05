# Local Testing Guide — LoanFlow AI

## Backend (`py/apps/loan-origination`)

```bash
cd py/apps/loan-origination
uv sync
uv run pytest tests -v
```

### Quick API smoke test

```bash
curl http://localhost:8002/healthz

curl -X POST http://localhost:8002/api/v1/loan/stream \
  -H "Content-Type: application/json" \
  -d '{"conversation_id":"local-test","message_id":"msg-1","message":"I want to apply for a mortgage","history":[]}'
```

## Frontend (`ts/apps/loan-ui`)

```bash
cd ts/apps/loan-ui
pnpm install
pnpm lint
pnpm type-check
pnpm dev
```

## Manual E2E

1. Run backend on `:8002`.
2. Run frontend on `:5174`.
3. Start a loan intake conversation.
4. Upload a sample document and verify quality/extraction behavior.
5. Confirm summary and approval-letter flow render correctly.

## Cleanup Notes

- Legacy non-loan endpoint checks are obsolete for this project scope.
- Focus validation on `/api/v1/loan/*` endpoints and streaming behavior.
