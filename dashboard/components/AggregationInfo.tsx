'use client';

import React from 'react';

interface AggregationMetadata {
  aggregation: string;
  aggregationWindow: string;
  estimatedPoints: number;
  actualPoints: number;
  timeRange: {
    start: string;
    end: string;
  };
}

interface AggregationInfoProps {
  metadata?: AggregationMetadata;
  className?: string;
}

export default function AggregationInfo({ metadata, className = '' }: AggregationInfoProps) {
  if (!metadata) return null;

  const isAggregated = metadata.aggregationWindow !== 'none' && metadata.aggregationWindow !== '';

  if (!isAggregated) return null;

  return (
    <div className={`bg-blue-50 border border-blue-200 rounded-lg p-4 ${className}`}>
      <div className="flex items-start space-x-3">
        <div className="flex-shrink-0">
          <svg
            className="h-5 w-5 text-blue-600"
            fill="currentColor"
            viewBox="0 0 20 20"
          >
            <path
              fillRule="evenodd"
              d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
              clipRule="evenodd"
            />
          </svg>
        </div>
        <div className="flex-1">
          <h3 className="text-sm font-semibold text-blue-900 mb-1">
            Data Sampling Active
          </h3>
          <p className="text-sm text-blue-800">
            <strong>{metadata.aggregation}</strong> — To optimize performance for this time range,
            data is being sampled with a <strong>{metadata.aggregationWindow}</strong> window.
            Showing {metadata.actualPoints.toLocaleString()} data points
            {metadata.estimatedPoints > 0 && ` (estimated ~${metadata.estimatedPoints.toLocaleString()})`}.
          </p>
          {metadata.aggregationWindow.includes('h') && (
            <p className="text-xs text-blue-700 mt-2">
              💡 Tip: For more granular data, select a shorter time range (e.g., last 7 days).
            </p>
          )}
          {(metadata.aggregationWindow.includes('d') || metadata.aggregationWindow.includes('w')) && (
            <p className="text-xs text-blue-700 mt-2">
              💡 Tip: Shorter time ranges will show more detailed data with higher resolution.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
