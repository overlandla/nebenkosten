import '@testing-library/jest-dom';
import { TextEncoder, TextDecoder } from 'util';

// Polyfill TextEncoder/TextDecoder for Node environment
global.TextEncoder = TextEncoder;
global.TextDecoder = TextDecoder as any;

// Minimal Request/Response/Headers mocks for Next.js compatibility
// These need to be defined before Next.js modules load
if (typeof global.Request === 'undefined') {
  class MockHeaders {
    private _headers: Map<string, string> = new Map();
    constructor(init?: HeadersInit) {
      if (init) {
        if (Array.isArray(init)) {
          init.forEach(([key, value]) => this._headers.set(key.toLowerCase(), value));
        } else if (init instanceof MockHeaders) {
          this._headers = new Map(init._headers);
        } else {
          Object.entries(init).forEach(([key, value]) => this._headers.set(key.toLowerCase(), value));
        }
      }
    }
    get(name: string) { return this._headers.get(name.toLowerCase()) || null; }
    set(name: string, value: string) { this._headers.set(name.toLowerCase(), value); }
    has(name: string) { return this._headers.has(name.toLowerCase()); }
    delete(name: string) { this._headers.delete(name.toLowerCase()); }
    forEach(fn: (value: string, key: string) => void) { this._headers.forEach(fn); }
    entries() { return this._headers.entries(); }
    keys() { return this._headers.keys(); }
    values() { return this._headers.values(); }
    [Symbol.iterator]() { return this._headers.entries(); }
  }

  class MockRequest {
    private _url: string;
    private _method: string;
    private _headers: MockHeaders;
    private _body: any;

    constructor(input: string | Request, init?: RequestInit) {
      this._url = typeof input === 'string' ? input : input.url;
      this._method = init?.method || 'GET';
      this._headers = new MockHeaders(init?.headers);
      this._body = init?.body;
    }

    get url() { return this._url; }
    get method() { return this._method; }
    get headers() { return this._headers; }

    async json() {
      if (typeof this._body === 'string') {
        return JSON.parse(this._body);
      }
      return this._body;
    }

    async text() {
      return typeof this._body === 'string' ? this._body : JSON.stringify(this._body);
    }
  }

  class MockResponse {
    body: any;
    status: number;
    statusText: string;
    headers: MockHeaders;
    ok: boolean;
    constructor(body?: BodyInit | null, init?: ResponseInit) {
      this.body = body;
      this.status = init?.status || 200;
      this.statusText = init?.statusText || 'OK';
      this.headers = new MockHeaders(init?.headers);
      this.ok = this.status >= 200 && this.status < 300;
    }
    async json() {
      return typeof this.body === 'string' ? JSON.parse(this.body) : this.body;
    }
    async text() {
      return typeof this.body === 'string' ? this.body : JSON.stringify(this.body);
    }
    static json(data: any, init?: ResponseInit) {
      return new MockResponse(JSON.stringify(data), {
        ...init,
        headers: { 'Content-Type': 'application/json', ...init?.headers },
      });
    }
  }

  global.Headers = MockHeaders as any;
  global.Request = MockRequest as any;
  global.Response = MockResponse as any;
}

// Mock environment variables
process.env.INFLUX_URL = 'http://test-influxdb:8086';
process.env.INFLUX_TOKEN = 'test-token-12345';
process.env.INFLUX_ORG = 'test-org';
process.env.INFLUX_BUCKET_RAW = 'test_raw';
process.env.INFLUX_BUCKET_PROCESSED = 'test_processed';
