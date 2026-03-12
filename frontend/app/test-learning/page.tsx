'use client';

import { useState } from 'react';
import { useLearningStore } from '../../state/useLearningStore';
import { useOutcomeTracker } from '../../state/useOutcomeTracker';

export default function ValidatonPage() {
  const { trackDismissal, trackCompletion } = useOutcomeTracker();
  const { getCalibration, getExplanation, calibrations, outcomeHistory } = useLearningStore();
  const [logs, setLogs] = useState<string[]>([]);

  const log = (msg: string) => setLogs(prev => [...prev, msg]);

  const runDismissalTest = () => {
    const key = 'test-pest-alert';
    log(`--- Starting Dismissal Test for ${key} ---`);
    log(`Initial Calibration: ${getCalibration(key)}`);

    // Simulate 3 dismissals
    trackDismissal(key, 'test-harness');
    trackDismissal(key, 'test-harness');
    trackDismissal(key, 'test-harness');

    setTimeout(() => {
       const cal = getCalibration(key);
       const expl = getExplanation(key);
       log(`After 3 dismissals: Calibration = ${cal.toFixed(2)}`);
       log(`Explanation: ${expl}`);

       if (cal < 1.0) {
           log('PASS: Confidence lowered.');
       } else {
           log('FAIL: Confidence did not lower.');
       }
    }, 100);
  };

  const runCompletionTest = () => {
    const key = 'test-pest-alert'; // reuse
    log(`--- Starting Completion Test ---`);
    
    // Simulate completions to restore confidence
    trackCompletion(key, 'test-harness');
    trackCompletion(key, 'test-harness');
    trackCompletion(key, 'test-harness');
    trackCompletion(key, 'test-harness');
    trackCompletion(key, 'test-harness');

    setTimeout(() => {
        const cal = getCalibration(key);
        log(`After 5 completions: Calibration = ${cal.toFixed(2)}`);
        
        if (cal > 0.8) { // Should have recovered somewhat
             log('PASS: Confidence recovering.');
        }
    }, 100);
  };

  return (
    <div style={{ padding: '2rem', color: '#fff', background: '#222', minHeight: '100vh', fontFamily: 'monospace' }}>
      <h1>Phase 8 Verification</h1>
      
      <div style={{ marginTop: '1rem', display: 'flex', gap: '1rem' }}>
        <button onClick={runDismissalTest} style={{ padding: '0.5rem 1rem', background: '#dc2626', color: 'white', border: 'none' }}>
           Run Dismissal Test
        </button>
        <button onClick={runCompletionTest} style={{ padding: '0.5rem 1rem', background: '#16a34a', color: 'white', border: 'none' }}>
           Run Recovery Test
        </button>
      </div>

      <div style={{ marginTop: '2rem', border: '1px solid #444', padding: '1rem' }}>
        <h3>Logs</h3>
        {logs.map((L, i) => <div key={i}>{L}</div>)}
      </div>

      <div style={{ marginTop: '2rem' }}>
          <h3>State Debug</h3>
          <pre style={{ fontSize: '0.8rem', color: '#888' }}>
              {JSON.stringify({ calibrations, historyCount: outcomeHistory.length }, null, 2)}
          </pre>
      </div>
    </div>
  );
}
