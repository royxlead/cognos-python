import React from 'react';
import { Lightbulb, Play, Eye, TrendingUp } from 'lucide-react';

function ReasoningView({ steps }) {
  const getConfidenceColor = (confidence) => {
    if (confidence >= 0.8) return 'text-green-600';
    if (confidence >= 0.6) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getConfidenceWidth = (confidence) => {
    return `${confidence * 100}%`;
  };

  return (
    <div className="mt-4 space-y-3">
      {steps.map((step, index) => (
        <div
          key={index}
          className="bg-gradient-to-r from-primary-50 to-blue-50 rounded-lg p-4 border border-primary-200"
        >
          <div className="flex items-center justify-between mb-3">
            <h4 className="font-semibold text-primary-900 flex items-center space-x-2">
              <span className="bg-primary-600 text-white rounded-full w-6 h-6 flex items-center justify-center text-sm">
                {step.step_number}
              </span>
              <span>Step {step.step_number}</span>
            </h4>
            
            <div className="flex items-center space-x-2">
              <span className={`text-sm font-medium ${getConfidenceColor(step.confidence)}`}>
                {(step.confidence * 100).toFixed(0)}%
              </span>
              <div className="w-20 bg-gray-200 rounded-full h-2">
                <div
                  className={`h-2 rounded-full ${
                    step.confidence >= 0.8 ? 'bg-green-600' :
                    step.confidence >= 0.6 ? 'bg-yellow-600' : 'bg-red-600'
                  }`}
                  style={{ width: getConfidenceWidth(step.confidence) }}
                />
              </div>
            </div>
          </div>

          {step.thought && (
            <div className="mb-2">
              <div className="flex items-start space-x-2">
                <Lightbulb className="w-4 h-4 text-yellow-600 mt-0.5 flex-shrink-0" />
                <div>
                  <span className="text-xs font-semibold text-gray-600 uppercase">Thought</span>
                  <p className="text-sm text-gray-800 mt-1">{step.thought}</p>
                </div>
              </div>
            </div>
          )}

          {step.action && (
            <div className="mb-2">
              <div className="flex items-start space-x-2">
                <Play className="w-4 h-4 text-blue-600 mt-0.5 flex-shrink-0" />
                <div>
                  <span className="text-xs font-semibold text-gray-600 uppercase">Action</span>
                  <p className="text-sm text-gray-800 mt-1">{step.action}</p>
                </div>
              </div>
            </div>
          )}

          {step.observation && (
            <div>
              <div className="flex items-start space-x-2">
                <Eye className="w-4 h-4 text-green-600 mt-0.5 flex-shrink-0" />
                <div>
                  <span className="text-xs font-semibold text-gray-600 uppercase">Observation</span>
                  <p className="text-sm text-gray-800 mt-1">{step.observation}</p>
                </div>
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

export default ReasoningView;
