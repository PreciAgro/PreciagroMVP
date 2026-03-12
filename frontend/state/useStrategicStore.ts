import { create } from 'zustand';
import { MultiSeasonContext, Season, StrategicPath } from '../core/models/StrategicContext';

// --- MOCK DATA ---

const MOCK_HISTORY: Season[] = [
    { id: '2023-harvest', year: 2023, type: 'historical', label: '2023 Harvest', status: 'completed' },
    { id: '2024-harvest', year: 2024, type: 'historical', label: '2024 Harvest', status: 'completed' },
];

const MOCK_CURRENT: Season = { 
    id: '2025-planting', year: 2025, type: 'current', label: '2025 Planting', status: 'active' 
};

const MOCK_PROJECTIONS: Season[] = [
    { id: '2025-harvest', year: 2025, type: 'projected', label: '2025 Harvest', status: 'future' },
    { id: '2026-season', year: 2026, type: 'projected', label: '2026 Season', status: 'future' },
    { id: '2027-season', year: 2027, type: 'projected', label: '2027 Season', status: 'future' },
];

const STRATEGY_CURRENT: StrategicPath = {
    id: 'strategy-continue',
    name: 'Continue Current Rotation',
    description: 'Maintain current crop cycle (Maize -> Soy). Low operational risk, predictable short-term.',
    timeframeYears: 3,
    overallConfidence: 'high',
    outcomes: [
        { label: 'Short-term Yield', value: 'Stable', trend: 'stable' },
        { label: 'Soil Nitrogen', value: 'Depleting slowly', trend: 'declining' }
    ],
    tradeOffs: [
        { 
            upside: 'No new equipment or training needed.', 
            downside: 'Soil nutrient depletion may require increased fertilizer input by year 3.', 
            uncertainty: 'low' 
        }
    ],
    risks: ['Fertilizer cost volatility', 'Pest resistance buildup']
};

const STRATEGY_LEGUME: StrategicPath = {
    id: 'strategy-legume',
    name: 'Introduce Legume Cover',
    description: 'Add a winter legume cover crop. Improves soil N, allows moisture retention.',
    timeframeYears: 3,
    overallConfidence: 'medium',
    outcomes: [
        { label: 'Short-term Yield', value: '-5% (Year 1)', trend: 'declining' },
        { label: 'Long-term Yield', value: '+10% (Year 3)', trend: 'improving' },
        { label: 'Soil Nitrogen', value: 'Regenerating', trend: 'improving' }
    ],
    tradeOffs: [
        { 
            upside: 'Reduces fertilizer dependency long-term.', 
            downside: 'Reduces cash crop planting window in Year 1.', 
            uncertainty: 'medium' 
        }
    ],
    risks: ['Establishment failure in dry winter', 'Timing conflict with main planting']
};

interface StrategicState {
    context: MultiSeasonContext;
    activeStrategyId: string | null; // The one currently being "viewed" or "simulated"
    comparedStrategyId: string | null; // The one being compared against
    isStrategicViewActive: boolean;

    // Actions
    activateStrategicView: () => void;
    deactivateStrategicView: () => void;
    setScenario: (id: string) => void;
    setComparison: (id: string | null) => void;
}

export const useStrategicStore = create<StrategicState>((set) => ({
    context: {
        currentSeasonId: MOCK_CURRENT.id,
        history: MOCK_HISTORY,
        projections: MOCK_PROJECTIONS,
        availableStrategies: [STRATEGY_CURRENT, STRATEGY_LEGUME]
    },
    activeStrategyId: STRATEGY_CURRENT.id,
    comparedStrategyId: null,
    isStrategicViewActive: false,

    activateStrategicView: () => set({ isStrategicViewActive: true }),
    deactivateStrategicView: () => set({ isStrategicViewActive: false }),
    setScenario: (id) => set({ activeStrategyId: id }),
    setComparison: (id) => set({ comparedStrategyId: id })
}));
