/**
 * Utility functions for time-aware InfluxDB query aggregation
 *
 * This module provides functions to determine optimal aggregation windows
 * based on the time range duration to prevent overwhelming the client
 * with too many data points while maintaining meaningful resolution.
 */

export interface AggregationConfig {
  window: string; // e.g., '1h', '6h', '1d', '1w'
  windowMs: number; // window duration in milliseconds
  fn: 'mean' | 'last' | 'sum'; // aggregation function
  description: string; // human-readable description
  shouldAggregate: boolean; // whether aggregation is needed
}

/**
 * Calculate the duration between two dates in days
 */
function getDurationInDays(start: Date, end: Date): number {
  const durationMs = end.getTime() - start.getTime();
  return durationMs / (1000 * 60 * 60 * 24);
}

/**
 * Parse InfluxDB relative time strings (e.g., '-90d', '-1y') to Date objects
 */
export function parseInfluxTime(timeStr: string, referenceDate: Date = new Date()): Date {
  if (timeStr === 'now()') {
    return referenceDate;
  }

  // Match patterns like -90d, -1y, -6mo, -24h
  const match = timeStr.match(/^-(\d+)(d|h|m|mo|y|w)$/);
  if (!match) {
    // If it's not a relative time, try parsing as ISO date
    const parsed = new Date(timeStr);
    if (!isNaN(parsed.getTime())) {
      return parsed;
    }
    // Default to reference date if parsing fails
    return referenceDate;
  }

  const [, amountStr, unit] = match;
  const amount = parseInt(amountStr, 10);
  const date = new Date(referenceDate);

  switch (unit) {
    case 'd': // days
      date.setDate(date.getDate() - amount);
      break;
    case 'h': // hours
      date.setHours(date.getHours() - amount);
      break;
    case 'm': // minutes
      date.setMinutes(date.getMinutes() - amount);
      break;
    case 'w': // weeks
      date.setDate(date.getDate() - (amount * 7));
      break;
    case 'mo': // months
      date.setMonth(date.getMonth() - amount);
      break;
    case 'y': // years
      date.setFullYear(date.getFullYear() - amount);
      break;
  }

  return date;
}

/**
 * Determine optimal aggregation window for raw meter readings
 *
 * Strategy:
 * - < 2 days: No aggregation (show all data points)
 * - 2-7 days: 15-minute aggregation
 * - 7-30 days: 1-hour aggregation
 * - 30-90 days: 6-hour aggregation
 * - 90-180 days: 12-hour aggregation
 * - 180-365 days: 1-day aggregation
 * - > 365 days: 1-week aggregation
 *
 * @param startDate - Start of time range
 * @param endDate - End of time range
 * @returns Aggregation configuration
 */
export function getOptimalAggregation(
  startDate: Date | string,
  endDate: Date | string
): AggregationConfig {
  // Parse dates if they're strings
  const start = typeof startDate === 'string'
    ? parseInfluxTime(startDate)
    : startDate;
  const end = typeof endDate === 'string'
    ? parseInfluxTime(endDate)
    : endDate;

  const durationDays = getDurationInDays(start, end);

  // No aggregation for short time ranges
  if (durationDays < 2) {
    return {
      window: '',
      windowMs: 0,
      fn: 'mean',
      description: 'Raw data (no aggregation)',
      shouldAggregate: false,
    };
  }

  // 2-7 days: 15-minute aggregation
  if (durationDays < 7) {
    return {
      window: '15m',
      windowMs: 15 * 60 * 1000,
      fn: 'mean',
      description: '15-minute averages',
      shouldAggregate: true,
    };
  }

  // 7-30 days: 1-hour aggregation
  if (durationDays < 30) {
    return {
      window: '1h',
      windowMs: 60 * 60 * 1000,
      fn: 'mean',
      description: 'Hourly averages',
      shouldAggregate: true,
    };
  }

  // 30-90 days: 6-hour aggregation
  if (durationDays < 90) {
    return {
      window: '6h',
      windowMs: 6 * 60 * 60 * 1000,
      fn: 'mean',
      description: '6-hour averages',
      shouldAggregate: true,
    };
  }

  // 90-180 days: 12-hour aggregation
  if (durationDays < 180) {
    return {
      window: '12h',
      windowMs: 12 * 60 * 60 * 1000,
      fn: 'mean',
      description: '12-hour averages',
      shouldAggregate: true,
    };
  }

  // 180-365 days: 1-day aggregation
  if (durationDays < 365) {
    return {
      window: '1d',
      windowMs: 24 * 60 * 60 * 1000,
      fn: 'mean',
      description: 'Daily averages',
      shouldAggregate: true,
    };
  }

  // > 365 days: 1-week aggregation
  return {
    window: '1w',
    windowMs: 7 * 24 * 60 * 60 * 1000,
    fn: 'mean',
    description: 'Weekly averages',
    shouldAggregate: true,
  };
}

/**
 * Determine optimal aggregation for consumption data
 * Consumption data is cumulative, so we use 'sum' instead of 'mean'
 * and can use slightly coarser aggregation since it's already processed
 */
export function getOptimalConsumptionAggregation(
  startDate: Date | string,
  endDate: Date | string
): AggregationConfig {
  const config = getOptimalAggregation(startDate, endDate);

  // For consumption data, use 'sum' instead of 'mean'
  return {
    ...config,
    fn: 'sum',
    description: config.shouldAggregate
      ? config.description.replace('averages', 'totals')
      : config.description,
  };
}

/**
 * Determine optimal aggregation for already-interpolated data
 * Interpolated data is already aggregated, so we need less aggressive sampling
 */
export function getOptimalInterpolatedAggregation(
  startDate: Date | string,
  endDate: Date | string,
  interpolationType: 'daily' | 'monthly'
): AggregationConfig {
  const start = typeof startDate === 'string'
    ? parseInfluxTime(startDate)
    : startDate;
  const end = typeof endDate === 'string'
    ? parseInfluxTime(endDate)
    : endDate;

  const durationDays = getDurationInDays(start, end);

  // For daily interpolated data
  if (interpolationType === 'daily') {
    // No aggregation for ranges < 180 days (already daily data)
    if (durationDays < 180) {
      return {
        window: '',
        windowMs: 0,
        fn: 'mean',
        description: 'Daily interpolated data',
        shouldAggregate: false,
      };
    }

    // 180-730 days (2 years): weekly aggregation
    if (durationDays < 730) {
      return {
        window: '1w',
        windowMs: 7 * 24 * 60 * 60 * 1000,
        fn: 'mean',
        description: 'Weekly averages',
        shouldAggregate: true,
      };
    }

    // > 2 years: monthly aggregation
    return {
      window: '1mo',
      windowMs: 30 * 24 * 60 * 60 * 1000,
      fn: 'mean',
      description: 'Monthly averages',
      shouldAggregate: true,
    };
  }

  // For monthly interpolated data - rarely needs further aggregation
  return {
    window: '',
    windowMs: 0,
    fn: 'mean',
    description: 'Monthly interpolated data',
    shouldAggregate: false,
  };
}

/**
 * Estimate the number of data points that will be returned
 * Useful for UI feedback and query optimization
 */
export function estimateDataPoints(
  startDate: Date | string,
  endDate: Date | string,
  aggregation: AggregationConfig
): number {
  const start = typeof startDate === 'string'
    ? parseInfluxTime(startDate)
    : startDate;
  const end = typeof endDate === 'string'
    ? parseInfluxTime(endDate)
    : endDate;

  const durationMs = end.getTime() - start.getTime();

  if (!aggregation.shouldAggregate) {
    // For raw data, estimate based on typical meter reading frequency
    // Most meters report every 5-15 minutes
    const avgReadingIntervalMs = 10 * 60 * 1000; // 10 minutes
    return Math.ceil(durationMs / avgReadingIntervalMs);
  }

  // For aggregated data, calculate based on window size
  return Math.ceil(durationMs / aggregation.windowMs);
}
