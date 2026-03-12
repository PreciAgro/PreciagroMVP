import React from 'react';
import { AssistedAction } from '@/core/models/AssistedAction';

interface ReversibilityGuardProps {
  action: AssistedAction;
  onUndo: () => void;
  onReset: () => void;
}

export const ReversibilityGuard: React.FC<ReversibilityGuardProps> = ({ action, onUndo, onReset }) => {
  return (
    <div className="bg-green-50 border border-green-200 rounded-lg p-6 shadow-sm animate-in fade-in zoom-in-95">
      <div className="flex items-center gap-3 mb-4">
        <div className="h-8 w-8 rounded-full bg-green-100 text-green-600 flex items-center justify-center">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        </div>
        <h3 className="text-lg font-bold text-green-900">
          Action Completed
        </h3>
      </div>

      <p className="text-green-800 text-sm mb-6">
        The system has finished the requested assistance for <strong>{action.title}</strong>.
      </p>

      <div className="flex gap-4">
        {action.reversible && (
          <button 
            onClick={onUndo}
            className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50 hover:border-gray-400 text-sm font-medium transition-colors"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h10a8 8 0 018 8v2M3 10l6 6m-6-6l6-6" />
            </svg>
            {action.reversalLabel || "Undo Action"}
          </button>
        )}

        <button 
          onClick={onReset}
          className="px-4 py-2 bg-green-700 text-white rounded-md hover:bg-green-800 text-sm font-medium transition-colors ml-auto"
        >
          Close & Continue
        </button>
      </div>
    </div>
  );
};
