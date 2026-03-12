'use client';

import { useFarmStore } from '../../state/farmStore';
import { MOCK_OBJECTS } from '../../core/models/FarmObject';
import { SCENARIO_HEALTHY } from '../../core/scenarios/healthy';
import { SCENARIO_FUNGAL } from '../../core/scenarios/fungalRisk';
import { SCENARIO_DROUGHT } from '../../core/scenarios/droughtStress';
import { ScenarioId } from '../../core/models/Scenario';
import { TimeWindow } from '../../core/models/TimeContext';
import { InsightList } from '../components/InsightList';
import { AssistedActionPanel } from '../components/assisted/AssistedActionPanel';
import { AssistedAction } from '../../core/models/AssistedAction';

import { StrategicCanvas } from '../components/strategic/StrategicCanvas';
import { useStrategicStore } from '../../state/useStrategicStore';

const SCENARIOS = [SCENARIO_HEALTHY, SCENARIO_FUNGAL, SCENARIO_DROUGHT];
const TIME_WINDOWS: TimeWindow[] = ['today', '7d', '30d', 'season', 'multi-season'];

const MOCK_ASSISTED_ACTION: AssistedAction = {
  id: 'action-1',
  title: 'Generate Treatment Plan',
  category: 'preparation',
  description: 'System can prepare a detailed treatment plan for the identified risk.',
  willDo: ['Calculate dosage based on field size', 'Check inventory availability', 'Draft application schedule'],
  willNotDo: ['Order chemicals', 'Assign workers', 'Start application'],
  userResponsibility: ['Verify dosage accuracy', 'Approve final schedule', 'Oversee application'],
  preparationSteps: [
    { id: '1', label: 'Analyzing Field Data', status: 'pending' },
    { id: '2', label: 'Checking Inventory', status: 'pending' }
  ],
  estimatedDurationSeconds: 2,
  risk: { level: 'low', implication: 'Miscalculation', mitigation: 'Manual review required' },
  reversible: true,
  reversalLabel: 'Discard Plan'
};

export default function FarmPage() {
  const { 
    selectedObject, 
    timeWindow, 
    scenarioId, 
    derivedInsights, 
    selectObject, 
    setTimeWindow, 
    setScenario 
  } = useFarmStore();

  const { isStrategicViewActive, activateStrategicView, deactivateStrategicView } = useStrategicStore();

  // Effect to handle entry/exit of strategic mode based on time window
  // In a real app, this might be more nuanced, but for Phase 9 demo:
  if (timeWindow === 'multi-season' && !isStrategicViewActive) {
      activateStrategicView();
  } else if (timeWindow !== 'multi-season' && isStrategicViewActive) {
      deactivateStrategicView();
  }

  return (
    <main style={{ 
      color: '#e0e0e0', 
      fontFamily: 'sans-serif',
      backgroundColor: '#0a0a0a',
      height: '100vh',
      width: '100vw',
      overflow: 'hidden',
      position: 'relative'
    }}>
      
      {/* STRATEGIC OVERLAY - Phase 9 */}
      {isStrategicViewActive && <StrategicCanvas />}

      {/* 
        LAYER 0: FARM SURFACE (Map/Canvas)
        This occupies the entire backdrop.
      */}
      <div style={{
        position: 'absolute',
        top: 0, 
        left: 0, 
        width: '100%', 
        height: '100%',
        backgroundColor: '#111',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 0,
        opacity: isStrategicViewActive ? 0 : 1, // Hide map when strategy is active
        transition: 'opacity 0.5s ease'
      }}>
         {/* Placeholder for Map */}
         <div style={{
             width: '80%', 
             height: '70%', 
             border: '1px solid #333', 
             borderRadius: '16px',
             display: 'flex',
             alignItems: 'center',
             justifyContent: 'center',
             color: '#333'
         }}>
             <span style={{ fontSize: '2rem', fontWeight: 700, opacity: 0.2 }}>FARM SURFACE LAYER</span>
         </div>
      </div>

      {/* 
        LAYER 1: CONTEXT CONTROLS (Functional UI)
        Positioned unintrusively at the bottom.
      */}
      <div style={{
        position: 'absolute',
        bottom: '2rem',
        left: '50%',
        transform: 'translateX(-50%)',
        zIndex: 60, // Ensure controls remain visible/clickable even in strategy mode (or maybe hidden? Strategy mode has its own controls)
        // Let's keep them visible to allow switching BACK to operational mode
        backgroundColor: 'rgba(20, 20, 20, 0.9)',
        padding: '1rem 2rem',
        borderRadius: '12px',
        border: '1px solid #333',
        backdropFilter: 'blur(8px)',
        display: 'flex',
        gap: '3rem',
        boxShadow: '0 4px 20px rgba(0,0,0,0.5)'
      }}>
         {/* Scenario (Demo) */}
         <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
             <span style={{ fontSize: '0.7rem', color: '#666', textTransform: 'uppercase' }}>Simulation</span>
             <select 
               value={scenarioId || ''} 
               onChange={(e) => setScenario(e.target.value as ScenarioId)}
               disabled={isStrategicViewActive} // Disable operational sims in strategy mode
               style={{ 
                   background: '#333', 
                   color: isStrategicViewActive ? '#555' : '#fff', 
                   border: 'none', 
                   padding: '0.4rem', 
                   borderRadius: '4px' 
               }}
             >
                 <option value="" disabled>Select Scenario</option>
                 {SCENARIOS.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
             </select>
         </div>

         {/* Object */}
         <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
             <span style={{ fontSize: '0.7rem', color: '#666', textTransform: 'uppercase' }}>Object</span>
             <div style={{ display: 'flex', gap: '0.5rem' }}>
                {MOCK_OBJECTS.map(obj => (
                    <button
                        key={obj.id}
                        onClick={() => selectObject(obj)}
                        disabled={isStrategicViewActive}
                        style={{
                            background: selectedObject?.id === obj.id ? '#fff' : '#333',
                            color: selectedObject?.id === obj.id ? '#000' : '#888',
                            border: 'none',
                            padding: '0.3rem 0.8rem',
                            borderRadius: '4px',
                            cursor: 'pointer',
                            fontSize: '0.85rem',
                            opacity: isStrategicViewActive ? 0.3 : 1
                        }}
                    >
                        {obj.name}
                    </button>
                ))}
             </div>
         </div>

         {/* Time */}
         <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
             <span style={{ fontSize: '0.7rem', color: '#666', textTransform: 'uppercase' }}>Time Horizon</span>
             <div style={{ display: 'flex', gap: '0.5rem' }}>
                {TIME_WINDOWS.map(t => (
                    <button
                        key={t}
                        onClick={() => setTimeWindow(t)}
                        style={{
                            background: timeWindow === t ? '#fff' : '#333',
                            color: timeWindow === t ? '#000' : '#888',
                            border: 'none',
                            padding: '0.3rem 0.8rem',
                            borderRadius: '4px',
                            cursor: 'pointer',
                            fontSize: '0.85rem',
                            textTransform: 'capitalize'
                        }}
                    >
                        {t}
                    </button>
                ))}
             </div>
         </div>
      </div>

      {/* 
        LAYER 2: INSIGHT OVERLAY (Peripheral Intelligence)
        Fixed to the right side, floating over the map.
      */}
      <div style={{
          position: 'absolute',
          top: '2rem',
          right: '2rem',
          zIndex: 20,
          pointerEvents: 'none', // Let clicks pass through empty areas
          opacity: isStrategicViewActive ? 0 : 1 // Hide operational insights in strategy mode
      }}>
          <div style={{ pointerEvents: 'auto' }}>
            <InsightList insights={derivedInsights} />
          </div>
      </div>

      {/* 
        LAYER 3: ASSISTED EXECUTION CHANNEL
        Specific location for authorized actions.
      */}
      <div style={{
          position: 'absolute',
          top: '2rem',
          left: '2rem',
          width: '400px', // Fixed width for panel
          zIndex: 30,
          opacity: isStrategicViewActive ? 0 : 1
      }}>
           {/* Only show if a scenario is active, for context */}
           {scenarioId && (
              <AssistedActionPanel action={MOCK_ASSISTED_ACTION} />
           )}
      </div>

    </main>
  );
}
