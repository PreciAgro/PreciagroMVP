'use client';

import { InsightList } from "./components/InsightList";
import { useFarmStore } from "../state/farmStore";
import { FarmMap } from "./components/FarmMap";
import { SystemAwarenessPanel } from "./components/SystemAwarenessPanel";
import { DemoControls } from "./components/DemoControls";

export default function Home() {
  const { derivedInsights } = useFarmStore();

  return (
    <>
      {/* Accessibility: Skip Link */}
      <a href="#main-content" className="skip-link">
        Skip to main content
      </a>
      
      <main 
        id="main-content"
        style={{ 
          minHeight: '100vh',
          maxWidth: '1280px',
          margin: '0 auto',
          padding: 'var(--space-4)',
          display: 'flex',
          flexDirection: 'column',
          gap: 'var(--space-4)'
        }}
      >
        <DemoControls />
        <FarmMap />
        
        {/* Accessibility: Section with proper heading hierarchy */}
        <section aria-label="System awareness">
          <SystemAwarenessPanel />
        </section>
        
        <section aria-label="Farm insights" aria-live="polite">
          <InsightList insights={derivedInsights} />
        </section>
      </main>
    </>
  );
}
