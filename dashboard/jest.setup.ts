import '@testing-library/jest-dom';
import { TextEncoder, TextDecoder } from 'util';

// Polyfill TextEncoder/TextDecoder for Node environment
global.TextEncoder = TextEncoder;
global.TextDecoder = TextDecoder as any;

// Mock Request and Response for Next.js edge runtime
global.Request = class Request {
  constructor(input: any, init?: any) {
    this.url = typeof input === 'string' ? input : input.url;
    this.method = init?.method || 'GET';
    this.headers = new Map(Object.entries(init?.headers || {}));
  }
  url: string;
  method: string;
  headers: Map<string, string>;
} as any;

global.Response = class Response {
  constructor(body?: any, init?: any) {
    this.body = body;
    this.status = init?.status || 200;
    this.headers = new Map(Object.entries(init?.headers || {}));
  }
  body: any;
  status: number;
  headers: Map<string, string>;
} as any;

// Mock environment variables
process.env.INFLUX_URL = 'http://test-influxdb:8086';
process.env.INFLUX_TOKEN = 'test-token-12345';
process.env.INFLUX_ORG = 'test-org';
process.env.INFLUX_BUCKET_RAW = 'test_raw';
process.env.INFLUX_BUCKET_PROCESSED = 'test_processed';
