---
applyTo: "**/*.ts,**/*.tsx,**/*.js,**/*.jsx"
---

# TypeScript/JavaScript Instructions

These instructions apply to all TypeScript and JavaScript files.

## TypeScript Rules

- **Strict mode** -- no implicit any
- **No `any` types** -- use `unknown` and narrow, or define proper types
- **Prefer interfaces** for object shapes
- **Use `type` for unions/primitives**

## Import Order

1. React imports
2. Third-party libraries
3. Internal aliases (`@/components`, `@/lib`)
4. Relative imports
5. Types (with `type` keyword)

```typescript
"use client";

import { useState } from "react";
import { useMsal } from "@azure/msal-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

import { LocalComponent } from "./local-component";

import type { ConversationRequest } from "@/types";
```

## Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Components | PascalCase | `ChatWindow.tsx` |
| Hooks | camelCase + `use` | `useConversation.ts` |
| Utilities | camelCase | `collectSignals.ts` |
| Constants | SCREAMING_SNAKE | `API_BASE_URL` |
| Types | PascalCase | `ConversationRequest` |

## Component Structure

```typescript
"use client"; // Only if client-side interactivity needed

// 1. Imports (in order above)

// 2. Types/Interfaces
interface Props {
  title: string;
  className?: string;
}

// 3. Constants (if component-specific)

// 4. Component
export function MyComponent({ title, className }: Props) {
  // Hooks first
  const [state, setState] = useState(false);

  // Handlers
  const handleClick = () => setState(true);

  // Render
  return (
    <div className={cn("base-styles", className)}>
      {title}
    </div>
  );
}
```

## Tailwind Class Organization

```typescript
className={cn(
  // 1. Layout
  "relative flex flex-col",
  // 2. Sizing
  "w-full p-4",
  // 3. Visual
  "bg-background rounded-lg border",
  // 4. States
  "hover:border-primary",
  // 5. Responsive
  "md:p-8 lg:flex-row",
  // 6. Conditional
  isActive && "border-primary",
  className
)}
```
