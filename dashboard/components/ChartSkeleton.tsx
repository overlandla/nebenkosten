import React from 'react';

/**
 * Loading skeleton for charts
 * Displays a placeholder animation while chart data is loading
 */

interface ChartSkeletonProps {
  title?: string;
  height?: number;
}

export default function ChartSkeleton({ title, height = 400 }: ChartSkeletonProps) {
  // Generate stable random heights using useMemo to avoid calling Math.random() during render
  const barHeights = React.useMemo(
    () => Array.from({ length: 12 }, () => Math.random() * 70 + 30),
    []
  );

  return (
    <div className="bg-white rounded-lg shadow-sm border border-neutral-200 p-6">
      {title && (
        <div className="mb-4">
          <div className="h-6 bg-neutral-200 rounded w-1/3 animate-pulse" />
        </div>
      )}
      <div className="space-y-3" style={{ height: `${height}px` }}>
        {/* Simulate chart bars/lines */}
        <div className="flex items-end justify-between h-full space-x-2">
          {barHeights.map((barHeight, i) => (
            <div
              key={i}
              className="flex-1 bg-neutral-200 rounded-t animate-pulse"
              style={{
                height: `${barHeight}%`,
                animationDelay: `${i * 50}ms`,
              }}
            />
          ))}
        </div>
        {/* X-axis placeholder */}
        <div className="flex justify-between pt-2">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="h-3 bg-neutral-200 rounded w-12 animate-pulse" />
          ))}
        </div>
      </div>
    </div>
  );
}
