export type FarmObjectType = 'field' | 'crop' | 'resource' | 'animal';

export interface FarmObject {
  id: string;
  type: FarmObjectType;
  name: string;
  region?: string; // Phase 10: Policy Awareness
  coordinates?: { lat: number; lng: number };
}

// Sample objects for the simulation
export const MOCK_OBJECTS: FarmObject[] = [
  { id: 'field-1', type: 'field', name: 'North Maize Field', region: 'midwest' },
  { id: 'field-2', type: 'field', name: 'East Pivot', region: 'wetlands' },
  { id: 'herd-1', type: 'animal', name: 'Brahman Herd A', region: 'midwest' },
];
