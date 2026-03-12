// Escalation levels define the visual loudness of the alert
// 0 = Passive (No motion, no color change)
// 1 = Visual Emphasis (Color shift, border)
// 2 = Motion-Assisted (Pulse, glow)
// 3 = Interruptive (Modal/Overlay - MAX 1 allowed globally)
export type EscalationLevel = 0 | 1 | 2 | 3;

export type AlertSeverity = 'low' | 'medium' | 'high' | 'critical';
export type AlertUrgency = 'now' | 'soon' | 'watch';
export type ExternalChannel = 'whatsapp' | 'sms';
export type EmergencyState = 'active' | 'acknowledged' | 'resolved';

export interface Alert {
  id: string;
  objectId: string; // The farm object this alert is attached to
  severity: AlertSeverity;
  urgency: AlertUrgency;
  escalationLevel: EscalationLevel;
  
  message: string;
  recommendedAction?: string;
  
  // Temporal context
  createdAt: string; // ISO date string
  validUntil?: string; // ISO date string
  
  // Metadata
  confidence: number; // 0.0 to 1.0
  source: string; // Specific model or rule engine ID
}

export interface EmergencyAlert extends Alert {
  escalationLevel: 3; // Emergencies are always Level 3
  externalChannels?: ExternalChannel[];
  consequenceIfIgnored: string;
  state: EmergencyState;
  acknowledgedAt?: string;
  externalLink?: string; // The deep link sent
}
