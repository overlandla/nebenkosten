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

export class MockWriteApi {
  private points: any[] = [];
  private shouldError: boolean = false;
  private errorMessage: string = 'Mock write error';

  writePoint(point: any): void {
    if (this.shouldError) {
      throw new Error(this.errorMessage);
    }
    this.points.push(point);
  }

  async close(): Promise<void> {
    if (this.shouldError) {
      throw new Error(this.errorMessage);
    }
    return Promise.resolve();
  }

  setShouldError(shouldError: boolean, message?: string): void {
    this.shouldError = shouldError;
    if (message) {
      this.errorMessage = message;
    }
  }

  getWrittenPoints(): any[] {
    return this.points;
  }

  clearPoints(): void {
    this.points = [];
  }
}

export class MockInfluxDB {
  private queryApi: MockQueryApi;
  private writeApi: MockWriteApi;

  constructor() {
    this.queryApi = new MockQueryApi();
    this.writeApi = new MockWriteApi();
  }

  getQueryApi(org: string): MockQueryApi {
    return this.queryApi;
  }

  getMockQueryApi(): MockQueryApi {
    return this.queryApi;
  }

  getWriteApi(org: string, bucket: string, precision?: string): MockWriteApi {
    return this.writeApi;
  }

  getMockWriteApi(): MockWriteApi {
    return this.writeApi;
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
