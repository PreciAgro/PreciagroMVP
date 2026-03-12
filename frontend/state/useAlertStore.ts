import { create } from 'zustand';
import { EmergencyAlert, Alert, EscalationLevel } from '../core/models/Alert';
import { useLearningStore } from './useLearningStore';

interface AlertState {
  activeEmergency: EmergencyAlert | null;
  
  // Actions
  triggerEmergency: (alert: Alert, details: Partial<EmergencyAlert>) => void;
  acknowledgeEmergency: () => void;
  resolveEmergency: () => void;
  
  // Logic
  shouldEscalateToExternal: (alert: Alert) => boolean;
  checkEmergencyCriteria: (insight: any) => void;
}

export const useAlertStore = create<AlertState>((set, get) => ({
  activeEmergency: null,

  triggerEmergency: (alert, details) => {
    const current = get().activeEmergency;
    
    // SAFETY RULE 10: At most one active emergency per user
    // If a new one comes in, we typically prioritize the NEW one if it's Critical+Now, 
    // or keep the existing one. For this specific implementation, we will REPLACEMENT 
    // strategy if the new one is 'critical', otherwise ignore.
    
    if (current && current.state !== 'resolved') {
        // Already handling an emergency.
        // If the new one is Critical and current is NOT, override.
        if (alert.severity === 'critical' && current.severity !== 'critical') {
            // Override
        } else {
            console.warn("Emergency blocked: One already active.");
            return; 
        }
    }

    const emergency: EmergencyAlert = {
        ...alert,
        escalationLevel: 3, 
        state: 'active',
        // Defaults if not provided in details (should be provided though)
        consequenceIfIgnored: details.consequenceIfIgnored || "Severe impact expected.",
        externalChannels: details.externalChannels || [],
        externalLink: details.externalLink
    };

    set({ activeEmergency: emergency });
    
    // Side Effect: Mock External Dispatch
    if (emergency.externalChannels && emergency.externalChannels.length > 0) {
        console.log(`[EXTERNAL DISPATCH] Sending to ${emergency.externalChannels.join(', ')}:`, emergency.message);
        console.log(`[EXTERNAL_LINK] ${emergency.externalLink || 'precigro://alert/' + emergency.id}`);
    }
  },

  acknowledgeEmergency: () => {
    const current = get().activeEmergency;
    if (current) {
        set({ activeEmergency: { ...current, state: 'acknowledged', acknowledgedAt: new Date().toISOString() } });
    }
  },

  resolveEmergency: () => {
    set({ activeEmergency: null });
  },

  shouldEscalateToExternal: (alert: Alert) => {
    // PHASE 5 LOGIC: 5/5 Criteria
    // 1. High/Critical
    // 2. Urgent (Now)
    // 3. Clear Action (checked by caller usually, but we check presence)
    // 4. Material Risk (implied by severity)
    // 5. Low Ambiguity (High Confidence > 0.8)

    if (alert.severity !== 'high' && alert.severity !== 'critical') return false;
    if (alert.urgency !== 'now') return false;
    if (!alert.recommendedAction) return false;
    if (alert.confidence < 0.8) return false;

    return true;
  },

  checkEmergencyCriteria: (insight: any) => {
      const state = get();
      
      // PHASE 8: Adaptive Intelligence
      const learningState = useLearningStore.getState();
      // Check contentKey - assuming insight.id is stable key
      const calibration = learningState.getCalibration(insight.id) || 1.0;
      
      // Safety Floor: Critical alerts cannot be suppressed below 90%
      const isCritical = insight.level === 'critical';
      const effectiveCalibration = isCritical ? Math.max(0.9, calibration) : calibration;
      
      const adaptiveConfidence = (insight.confidence || 0.85) * effectiveCalibration;

      // Map Insight to Alert candidate
      const urgency = (insight.type === 'risk' && insight.level === 'critical') ? 'now' : 'watch';
      const severity = insight.level === 'critical' ? 'critical' : (insight.level === 'warning' ? 'high' : 'medium');
      
      const candidate: Alert = {
          id: `alert-${insight.id}`,
          objectId: 'current-object', // Context dependent
          severity: severity as any,
          urgency: urgency as any,
          escalationLevel: 0,
          message: insight.title,
          recommendedAction: insight.recommendation,
          confidence: adaptiveConfidence,
          createdAt: new Date().toISOString(),
          source: 'insight-engine'
      };

      if (state.shouldEscalateToExternal(candidate)) {
          state.triggerEmergency(candidate, {
              consequenceIfIgnored: insight.riskIfIgnored || "Significant loss likely.",
              externalChannels: ['whatsapp']
          });
      }
  }
}));
