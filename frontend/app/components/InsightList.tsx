'use client';

import { AnimatePresence } from 'framer-motion';
import { Insight } from '../../core/models/Insight';
import { InsightCard } from './InsightCard';

interface InsightListProps {
  insights: Insight[];
}

export function InsightList({ insights }: InsightListProps) {
  // Deterministic Sorting:
  // 1. Severity (Critical > Warning > Info > Success)
  // 2. Confidence (Higher first) - Proxy for relevance/truth
  
  const sortedInsights = [...insights].sort((a, b) => {
    const severityScore = (level: string) => {
      switch (level) {
        case 'critical': return 4;
        case 'warning': return 3;
        case 'info': return 2;
        case 'success': return 1;
        default: return 0;
      }
    };

    const diff = severityScore(b.level) - severityScore(a.level);
    if (diff !== 0) return diff;
    
    return b.confidence - a.confidence;
  });

  return (
    <div style={{ width: '100%', maxWidth: '380px' }}>
      <AnimatePresence mode="popLayout">
        {sortedInsights.map((insight) => (
          <InsightCard key={insight.id} insight={insight} />
        ))}
      </AnimatePresence>
    </div>
  );
}
