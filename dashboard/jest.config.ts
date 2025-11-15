import type { Config } from 'jest';

// Add any custom config to be passed to Jest
const config: Config = {
  coverageProvider: 'v8',
  testEnvironment: 'jsdom',
  setupFilesAfterEnv: ['<rootDir>/jest.setup.ts'],
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/$1',
  },
  testMatch: [
    '**/__tests__/**/*.[jt]s?(x)',
    '**/?(*.)+(spec|test).[jt]s?(x)',
  ],
  testPathIgnorePatterns: [
    '/node_modules/',
    '/__tests__/mocks/',
    '/__tests__/fixtures/',
  ],
  collectCoverageFrom: [
    'app/**/*.{js,jsx,ts,tsx}',
    'components/**/*.{js,jsx,ts,tsx}',
    'lib/**/*.{js,jsx,ts,tsx}',
    'types/**/*.{js,jsx,ts,tsx}',
    '!**/*.d.ts',
    '!**/node_modules/**',
    '!**/.next/**',
    '!**/coverage/**',
    '!**/jest.config.ts',
    '!**/jest.setup.ts',
  ],
  // Coverage thresholds for tested files
  // API routes have lower coverage due to Next.js edge runtime mocking challenges
  coverageThreshold: {
    'lib/influxdb.ts': {
      branches: 75,
      functions: 100,
      lines: 100,
      statements: 100,
    },
    'components/ChartSkeleton.tsx': {
      branches: 100,
      functions: 100,
      lines: 100,
      statements: 100,
    },
    'components/ConsumptionChart.tsx': {
      branches: 100,
      functions: 50,
      lines: 100,
      statements: 100,
    },
    'components/TimeRangeSelector.tsx': {
      branches: 100,
      functions: 60,
      lines: 100,
      statements: 100,
    },
    'components/MeterReadingsChart.tsx': {
      branches: 75,
      functions: 20,
      lines: 80,
      statements: 80,
    },
    'components/ErrorBoundary.tsx': {
      branches: 70,
      functions: 65,
      lines: 85,
      statements: 85,
    },
    'app/api/meters/route.ts': {
      branches: 85,
      functions: 100,
      lines: 90,
      statements: 90,
    },
  },
  transform: {
    '^.+\\.(ts|tsx)$': ['ts-jest', {
      tsconfig: {
        jsx: 'react-jsx',
      },
    }],
  },
};

export default config;
