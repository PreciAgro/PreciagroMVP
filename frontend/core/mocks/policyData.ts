import { PolicyBoundary } from '../models/PolicyContext';

export const MOCK_POLICIES: PolicyBoundary[] = [
  {
    id: 'water-conservation-2025',
    type: 'advisory',
    description: 'Regional water conservation recommended during dry season',
    severityLevel: 'caution',
    source: 'Regional Water Authority',
    applicableContext: {
      region: 'midwest',
      cropTypes: ['maize', 'soy'],
      effectiveFrom: '2025-06-01',
      effectiveUntil: '2025-09-30'
    }
  },
  {
    id: 'pollinator-protection-zone',
    type: 'environmental',
    description: 'Pollinator protection zone: minimize pesticide use during flowering',
    severityLevel: 'info',
    source: 'Environmental Stewardship Council',
    applicableContext: {
      region: 'all',
      cropTypes: ['sunflower', 'canola', 'soy', 'fruit'],
      effectiveFrom: '2025-01-01'
    }
  },
  {
    id: 'buffer-zone-regulation',
    type: 'regulatory',
    description: 'Maintain 10m buffer zone from waterways for chemical application',
    severityLevel: 'caution',
    source: 'Department of Agriculture',
    applicableContext: {
      region: 'wetlands',
      cropTypes: [], // Applies to all
      effectiveFrom: '2024-01-01'
    }
  }
];
