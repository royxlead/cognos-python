import React from 'react';

const LoadingSpinner = ({ size = 'md' }) => {
  const sizeClasses = {
    sm: 'w-4 h-4',
    md: 'w-6 h-6',
    lg: 'w-8 h-8',
  };

  return (
    <div className="flex items-center justify-center">
      <div className={`relative ${sizeClasses[size]}`}>
        <div className="absolute inset-0 rounded-full border-2 border-primary/20 animate-pulse" />
        <div className="absolute inset-1 rounded-full border-2 border-transparent border-t-primary animate-spin" />
        <div className="absolute inset-1/2 -translate-x-1/2 -translate-y-1/2 w-1 h-1 bg-primary rounded-full animate-glow" />
      </div>
    </div>
  );
};

export default LoadingSpinner;
