---
applyTo: "ts/apps/loan-ui/**"
---

# Loan Origination Frontend Instructions

## Overview

The **Loan Origination Frontend** is a React + Vite SPA that provides a
conversational interface for mortgage loan applications.

## Tech Stack

- **React 19** + **Vite 6** (NOT Next.js)
- **TypeScript** — strict mode, no `any`
- **Tailwind CSS 3** with shadcn/ui-style design tokens
- **pnpm** for package management
- **lucide-react** for icons
- **react-markdown** + **remark-gfm** for rich message rendering
- **react-router-dom** for routing

## Key Paths

| Path | Purpose |
|------|---------|
| `src/App.tsx` | App root with routing |
| `src/main.tsx` | React DOM entry point |
| `src/types.ts` | TypeScript interfaces |
| `src/lib/api.ts` | Backend API client with SSE streaming |
| `src/hooks/use-conversation.tsx` | Conversation state management context |
| `src/components/chat/` | Chat UI components |
| `src/components/upload/` | Document upload modal |
| `src/components/layout/` | Header + layout wrapper |

## Running Locally

```bash
cd ts/apps/loan-ui
pnpm install
pnpm dev        # → http://localhost:5174
```

Ensure the backend is running on port 8002. The Vite dev server proxies
`/api` and `/healthz` requests automatically.

## Design Tokens

The frontend uses a **blue primary color** (HSL 221 83% 53%) to differentiate
the financial services experience from generic app themes.

## Document Upload Flow

1. User clicks the paperclip icon in the chat input or "Upload Doc" in the header
2. File is read as base64 on the client
3. The document is stored as `pendingDocument` in the conversation context
4. On the next `sendMessage`, the base64 content is sent as `document_context`
5. The agent processes it via `validate_document_quality` + `extract_document_fields`

## Conventions

- Keep TypeScript strict; avoid `any`
- Keep UI logic in `src/components`, `src/hooks`, `src/lib`
- Follow the existing component naming pattern (kebab-case files, PascalCase exports)
- Use `cn()` utility for conditional class merging
- SSE protocol: `delta`/`done`/`error` event types
