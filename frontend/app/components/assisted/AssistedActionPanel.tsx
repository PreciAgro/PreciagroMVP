import React from 'react';
import { useAssistedExecutionStore } from '@/state/useAssistedExecutionStore';
import { AssistedAction } from '@/core/models/AssistedAction';
import { AuthorizationStep } from './AuthorizationStep';
import { ReversibilityGuard } from './ReversibilityGuard';

interface AssistedActionPanelProps {
  action: AssistedAction;
}

export const AssistedActionPanel: React.FC<AssistedActionPanelProps> = ({ action }) => {
  const { 
    currentAction, 
    status, 
    progress, 
    selectAction, 
    startPreparation, 
    cancelPreparation, 
    confirmAuthorization, 
    executeAction,
    undoLastAction,
    reset 
  } = useAssistedExecutionStore();

  const isActive = currentAction?.id === action.id;
  const isBusyWithOther = !!currentAction && currentAction.id !== action.id;

  if (isBusyWithOther) {
    return (
      <div className="opacity-50 pointer-events-none p-4 border border-gray-200 rounded-lg">
        <p className="text-gray-400 text-sm">Assistance unavailable (System busy)</p>
      </div>
    );
  }

  // IDLE STATE: Offer Assistance (Task 10: Expert Margin Note)
  if (!isActive || status === 'idle') {
    return (
      <div className="group pl-4 border-l-2 border-gray-200 hover:border-gray-400 transition-colors py-2 my-4">
        <div className="flex flex-col gap-2">
          
          <div className="flex justify-between items-start">
             <div>
                <h4 className="font-medium text-gray-500 text-xs uppercase tracking-widest flex items-center gap-2">
                  <span>✦</span> Available Intervention
                </h4>
                <p className="text-gray-400 text-sm mt-1 font-light leading-relaxed max-w-md">
                  {action.description}
                </p>
             </div>
             
             <button
                onClick={() => {
                  selectAction(action);
                  startPreparation(); 
                }}
                className="opacity-0 group-hover:opacity-100 transition-opacity px-3 py-1 bg-gray-100 text-gray-800 text-xs hover:bg-gray-200 rounded-sm"
              >
                Draft Proposal
              </button>
          </div>

          {/* Task 11: Subtle Reassurance */}
          <p className="text-[10px] text-gray-300 italic opacity-0 group-hover:opacity-60 transition-opacity delay-100">
             You remain in full control. Nothing executes without approval.
          </p>

        </div>
      </div>
    );
  }

  // PREPARING STATE
  if (status === 'preparing') {
    return (
      <div className="bg-white border border-gray-200 p-6 rounded-lg shadow-sm">
        <h3 className="text-gray-900 font-semibold mb-2">Preparing {action.title}...</h3>
        <div className="w-full bg-gray-200 rounded-full h-2.5 mb-4">
          <div 
            className="bg-indigo-600 h-2.5 rounded-full transition-all duration-500 ease-out" 
            style={{ width: `${progress}%` }}
          ></div>
        </div>
        <p className="text-xs text-gray-500 text-right">System calculating...</p>
      </div>
    );
  }

  // READY FOR REVIEW STATE
  if (status === 'ready_for_review') {
      return (
      <div className="bg-white border border-indigo-200 p-6 rounded-lg shadow-md animate-in fade-in">
        <div className="flex justify-between items-start mb-4">
          <div>
             <h3 className="text-gray-900 font-bold text-lg">Preparation Complete</h3>
             <p className="text-gray-600 text-sm">Review the prepared plan before authorizing.</p>
          </div>
           <button 
            onClick={cancelPreparation}
            className="text-gray-400 hover:text-red-500 text-sm"
          >
            Cancel
          </button>
        </div>
        
        <div className="bg-gray-50 p-4 rounded-md mb-6 font-mono text-sm text-gray-700 border border-gray-200">
           {/* Mock preview of prepared data */}
           <p className="mb-2"><strong>OUTPUT SUMMARY:</strong></p>
           <ul className="list-disc pl-4 space-y-1">
             <li>Generated {action.title} Draft</li>
             <li>Validated inputs: OK</li>
             <li>Risk Level: {action.risk.level.toUpperCase()}</li>
           </ul>
        </div>

        <button 
          onClick={confirmAuthorization}
          className="w-full py-3 bg-indigo-600 text-white font-bold rounded-md hover:bg-indigo-700 hover:shadow-lg transition-all"
        >
          Review for Authorization
        </button>
      </div>
    );
  }

  // AUTHORIZING STATE
  if (status === 'authorizing') {
    return (
      <AuthorizationStep 
        action={action}
        onConfirm={executeAction}
        onCancel={() => reset()} // Or cancelPreparation to go back? Reset is safer to exit.
      />
    );
  }

  // EXECUTING STATE
  if (status === 'executing') {
    return (
      <div className="bg-white border border-gray-200 p-8 rounded-lg shadow-sm flex flex-col items-center justify-center">
         <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-indigo-600 mb-4"></div>
         <p className="text-gray-700 font-medium">Executing Action...</p>
         <p className="text-xs text-gray-400 mt-2">Please wait. Do not close this window.</p>
      </div>
    );
  }

  // COMPLETED STATE
  if (status === 'completed') {
    return (
      <ReversibilityGuard 
        action={action}
        onUndo={undoLastAction}
        onReset={reset}
      />
    );
  }

  return null;
};
