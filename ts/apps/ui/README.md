# VIN Insight Frontend

React 19 + Vite SPA for VIN report conversations.

## Scripts

```bash
pnpm dev
pnpm build
pnpm lint
pnpm type-check
```

## Current Structure

```text
src/
  App.tsx
  main.tsx
  index.css
  types.ts
  components/
    chat/
      chat-page.tsx
      chat-message-list.tsx
      chat-message.tsx
      chat-input.tsx
      chat-empty-state.tsx
      typing-indicator.tsx
      trace-panel.tsx
      toast.tsx
    layout/
      app-layout.tsx
      app-header.tsx
  hooks/
    use-conversation.tsx
  lib/
    api.ts
    utils.ts
```

## Notes

- Auth-specific modules (`use-auth.tsx`, `lib/auth.ts`) and browser-signal module (`lib/signals.ts`) were removed.
- Source-of-truth code is in `src`; `dist` and `*.tsbuildinfo` are generated artifacts.
- `lib/api.ts` calls `POST /api/v1/vin-insight`.
