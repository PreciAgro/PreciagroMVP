'use client';

import { useFarmStore } from '../../../state/farmStore';
import { useAlertStore } from '../../../state/useAlertStore';

export function DeepLinkSimulator() {
  const { setScenario, setTimeWindow, selectObject } = useFarmStore();
  const { activeEmergency } = useAlertStore();

  const handleSimulateLink = () => {
    console.log("Simulating Deep Link Access...");
    // 1. Force Scenario that contains a known emergency
    setScenario('demo_drought_stress');
    
    // 2. Force TimeContext that triggers the critical rule
    setTimeWindow('7d');
    
    // 3. Select the object
    // In a real app, we'd lookup object by ID. Here we mock it.
    selectObject({
        id: 'field-a',
        name: 'Maize Field A',
        type: 'field'
    });
    
    // The farmStore side-effect should trigger the emergency check
    // and the Overlay should appear immediately.
  };

  if (activeEmergency) return null; // Hide if emergency is already active (don't clutter)

  return (
    <div style={{
      position: 'fixed',
      bottom: '1rem',
      right: '1rem',
      zIndex: 100,
      opacity: 0.5,
      transition: 'opacity 0.2s'
    }}
    onMouseEnter={(e) => e.currentTarget.style.opacity = '1'}
    onMouseLeave={(e) => e.currentTarget.style.opacity = '0.5'}
    >
      <button
        onClick={handleSimulateLink}
        style={{
          background: '#333',
          color: '#fff',
          border: '1px solid #555',
          padding: '0.5rem 1rem',
          fontSize: '0.75rem',
          borderRadius: '4px',
          cursor: 'pointer'
        }}
      >
        🐛 Sim WhatsApp Link
      </button>
    </div>
  );
}
