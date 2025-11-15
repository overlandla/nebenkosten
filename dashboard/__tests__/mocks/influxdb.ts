/**
 * Mock utilities for InfluxDB client
 * Inspired by Dagster test patterns
 */

import { InfluxDB } from '@influxdata/influxdb-client';

export class MockQueryApi {
  private mockData: any[] = [];
  private shouldError: boolean = false;
  private errorMessage: string = 'Mock query error';

  setMockData(data: any[]): void {
    this.mockData = data;
  }

  setShouldError(shouldError: boolean, message?: string): void {
    this.shouldError = shouldError;
    if (message) {
      this.errorMessage = message;
    }
  }

  queryRows(
    query: string,
    callbacks: {
      next: (row: string[], tableMeta: any) => void;
      error: (error: Error) => void;
      complete: () => void;
    }
  ): void {
    if (this.shouldError) {
      callbacks.error(new Error(this.errorMessage));
      return;
    }

    // Create a mock tableMeta
    const mockTableMeta = {
      toObject: (row: string[]): any => {
        // Simple implementation that converts array to object
        return row[0] ? JSON.parse(row[0]) : {};
      },
    };

    // Call next for each mock data item
    this.mockData.forEach((data) => {
      callbacks.next([JSON.stringify(data)], mockTableMeta);
    });

    // Call complete
    callbacks.complete();
  }
}

export class MockInfluxDB {
  private queryApi: MockQueryApi;

  constructor() {
    this.queryApi = new MockQueryApi();
  }

  getQueryApi(org: string): MockQueryApi {
    return this.queryApi;
  }

  getMockQueryApi(): MockQueryApi {
    return this.queryApi;
  }
}

/**
 * Create a mock InfluxDB instance for testing
 */
export function createMockInfluxDB(): MockInfluxDB {
  return new MockInfluxDB();
}

/**
 * Mock the InfluxDB module
 */
export function mockInfluxDBModule(): void {
  jest.mock('@influxdata/influxdb-client', () => ({
    InfluxDB: jest.fn().mockImplementation(() => createMockInfluxDB()),
  }));
}
