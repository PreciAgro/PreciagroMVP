import { create } from 'zustand';
import { TimeWindow } from '../core/models/TimeContext';
import { FarmObject } from '../core/models/FarmObject';
import { Insight } from '../core/models/Insight';
import { ScenarioId } from '../core/models/Scenario';
import { resolveInsights } from '../core/intelligence/resolveInsights';
import { useAlertStore } from './useAlertStore';

// The Single Source of Truth for the Application
import { usePolicyStore } from './usePolicyStore';

// The Single Source of Truth for the Application
export interface FarmState {
  // --- CONTEXT ---
  selectedObject: FarmObject | null;
  timeWindow: TimeWindow;
  scenarioId: ScenarioId | null;

  // --- DERIVED INTELLIGENCE ---
  derivedInsights: Insight[];

  // --- ACTIONS ---
  // These are the "Knobs" intended for the UI or Demo Controller
  selectObject: (object: FarmObject | null) => void;
  setTimeWindow: (window: TimeWindow) => void;
  setScenario: (id: ScenarioId | null) => void;
}

export const useFarmStore = create<FarmState>((set, get) => ({
  selectedObject: null,
  timeWindow: 'today',
  scenarioId: null,
  derivedInsights: [],

  selectObject: (object) => {
    const state = get();
    // Resolve insights immediately using the NEW object and EXISTING other state
    const insights = resolveInsights(object, state.timeWindow, state.scenarioId);
    set({ selectedObject: object, derivedInsights: insights });
    
    // Check for emergencies
    insights.forEach(insight => useAlertStore.getState().checkEmergencyCriteria(insight));

    // PHASE 10: Update Policy Context
    if (object) {
      usePolicyStore.getState().updatePolicyContext({
        region: object.region || 'midwest', // Default to midwest if undefined
        cropType: object.type,
        season: state.timeWindow === 'today' ? 'active' : 'planning' 
      });
    }
  },

  setTimeWindow: (window) => {
    const state = get();
    const insights = resolveInsights(state.selectedObject, window, state.scenarioId);
    set({ timeWindow: window, derivedInsights: insights });

    // Check for emergencies
    insights.forEach(insight => useAlertStore.getState().checkEmergencyCriteria(insight));
    
    // PHASE 10: Update Policy Context (Seasonality may change)
     if (state.selectedObject) {
       usePolicyStore.getState().updatePolicyContext({
        region: state.selectedObject.region || 'midwest',
        cropType: state.selectedObject.type,
        season: window === 'today' ? 'active' : 'planning' 
      });
    }
  },

  setScenario: (id) => {
    const state = get();
    const insights = resolveInsights(state.selectedObject, state.timeWindow, id);
    set({ scenarioId: id, derivedInsights: insights });

    // Check for emergencies
    insights.forEach(insight => useAlertStore.getState().checkEmergencyCriteria(insight));
    
    // Policy context typically stable across scenarios unless scenario IS a policy change
    // For now we don't auto-update policy on scenario change unless needed
  },
}));
