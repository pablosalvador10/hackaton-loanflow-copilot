/**
 * App layout — full-height chat layout with header.
 * The main content area fills all available vertical space
 * so the chat input stays at the bottom.
 */

import { Outlet } from "react-router-dom";
import { AppHeader } from "./app-header";

export function AppLayout() {
  return (
    <div className="relative bg-background h-screen flex flex-col overflow-hidden">
      <AppHeader />

      {/* Main content — expands to fill, no overflow on outer container */}
      <main className="pt-[60px] md:pt-[64px] flex-1 flex flex-col min-h-0">
        <Outlet />
      </main>
    </div>
  );
}
