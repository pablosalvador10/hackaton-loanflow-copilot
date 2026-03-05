---
applyTo: "ts/apps/ui/**"
---

# Frontend Instructions

These instructions apply when working with files in the `ts/apps/ui/` directory.

## Tech Stack

- **Framework:** React + Vite (NOT Next.js -- this is an SPA)
- **Language:** TypeScript (strict mode)
- **Styling:** Tailwind CSS + shadcn/ui
- **Package Manager:** pnpm
- **Auth:** MSAL (`@azure/msal-browser`, `@azure/msal-react`)

## Critical Rules

1. **No `any` types** -- use proper TypeScript types
2. **Use shadcn/ui components** -- don't create custom primitives
3. **Collect browser signals** -- device_id, cookie_id, UTM, referrer, UA Client Hints
4. **Send correlation headers** -- `x-conversation-id` and `x-message-id` on every API call
5. **MSAL for auth** -- use `@azure/msal-react` hooks, support dev mode bypass
6. **Chat UI** -- message list, input box, routing CTA buttons (contact sales, get support)

## Component Pattern

```typescript
"use client"; // Only if needed

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface ComponentProps {
  // Props with types
}

export function Component({ ...props }: ComponentProps) {
  // Implementation
}
```

## File Structure

| Type | Location |
|------|----------|
| Components | `src/components/` |
| UI Components | `src/components/ui/` |
| Layout Components | `src/components/layout/` |
| Chat Components | `src/components/chat/` |
| Routing Components | `src/components/routing/` |
| Utilities | `src/lib/` |
| Hooks | `src/hooks/` |
| Types | `src/types/` |

## Browser Signal Collection

The frontend must collect and send these signals to the backend:
- `conversation_id` (sessionStorage UUID)
- `device_id` (localStorage UUID)
- `cookie_id` (first-party cookie UUID)
- `referrer`, `utm_*`, `language`, `timezone`, `screen`, `user_agent`, `ua_ch`

## Commands

```bash
pnpm dev        # Development server (port 5173)
pnpm build      # Production build
pnpm lint       # Run ESLint
pnpm type-check # TypeScript check
```

## Related Documentation

See [coding-standards.md](../coding-standards.md) for detailed frontend standards.
