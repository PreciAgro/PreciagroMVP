import React, { useState } from 'react';
import { AssistedAction } from '@/core/models/AssistedAction';

interface AuthorizationStepProps {
  action: AssistedAction;
  onConfirm: () => void;
  onCancel: () => void;
}

export const AuthorizationStep: React.FC<AuthorizationStepProps> = ({ action, onConfirm, onCancel }) => {
  const [hasReviewed, setHasReviewed] = useState(false);

  return (
    <div className="bg-white border border-yellow-500 rounded-lg p-6 shadow-sm animate-in fade-in slide-in-from-bottom-2">
      <h3 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
        <span className="text-yellow-600">⚠️</span> 
        Review & Authorize
      </h3>

      <div className="space-y-6">
        {/* Section 1: What will happen */}
        <div className="bg-blue-50 p-4 rounded-md border border-blue-100">
          <h4 className="text-sm font-semibold text-blue-900 uppercase tracking-wider mb-2">
            The System Will Prepare:
          </h4>
          <ul className="list-disc list-inside space-y-1 text-blue-800 text-sm">
            {action.willDo.map((item, i) => (
              <li key={i}>{item}</li>
            ))}
          </ul>
        </div>

        {/* Section 2: What will NOT happen */}
        <div className="bg-red-50 p-4 rounded-md border border-red-100">
           <h4 className="text-sm font-semibold text-red-900 uppercase tracking-wider mb-2">
            The System Will NOT Do:
          </h4>
          <ul className="list-disc list-inside space-y-1 text-red-800 text-sm">
            {action.willNotDo.map((item, i) => (
              <li key={i}>{item}</li>
            ))}
          </ul>
        </div>

        {/* Section 3: User Responsibility */}
        <div className="bg-gray-50 p-4 rounded-md border border-gray-200">
           <h4 className="text-sm font-semibold text-gray-700 uppercase tracking-wider mb-2">
            Your Responsibility:
          </h4>
          <ul className="list-disc list-inside space-y-1 text-gray-600 text-sm">
            {action.userResponsibility.map((item, i) => (
              <li key={i}>{item}</li>
            ))}
          </ul>
        </div>
      </div>

      <div className="mt-8 border-t border-gray-100 pt-6">
        <label className="flex items-start gap-3 cursor-pointer group">
          <div className="relative flex items-center">
            <input 
              type="checkbox" 
              checked={hasReviewed}
              onChange={(e) => setHasReviewed(e.target.checked)}
              className="peer h-5 w-5 cursor-pointer appearance-none rounded-md border border-gray-300 transition-all checked:border-green-600 checked:bg-green-600 hover:border-green-500"
            />
            <svg className="pointer-events-none absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 text-white opacity-0 peer-checked:opacity-100 placeholder-check" width="12" height="12" viewBox="0 0 12 12" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M10 3L4.5 8.5L2 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
          <span className="text-sm text-gray-600 group-hover:text-gray-900 transition-colors">
            I understand that I am responsible for verifying and executing the final action.
          </span>
        </label>

        <div className="flex gap-4 mt-6">
           <button 
            onClick={onCancel}
            className="px-4 py-2 text-gray-600 hover:text-gray-800 font-medium text-sm transition-colors"
          >
            Cancel
          </button>
          
          <button 
            onClick={onConfirm}
            disabled={!hasReviewed}
            className={`
              flex-1 px-6 py-2 rounded-md font-bold shadow-sm transition-all
              ${hasReviewed 
                ? 'bg-green-700 text-white hover:bg-green-800 hover:shadow-md' 
                : 'bg-gray-200 text-gray-400 cursor-not-allowed'}
            `}
          >
            Authorize & Execute
          </button>
        </div>
      </div>
    </div>
  );
};
