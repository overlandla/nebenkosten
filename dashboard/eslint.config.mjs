import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
  ]),
  // Custom rule overrides
  {
    rules: {
      // Allow unescaped entities in JSX (quotes, apostrophes)
      "react/no-unescaped-entities": "off",
      // Allow unused vars if they start with underscore
      "@typescript-eslint/no-unused-vars": [
        "warn",
        {
          argsIgnorePattern: "^_",
          varsIgnorePattern: "^_",
        },
      ],
    },
  },
  // Relaxed rules for test files and mocks
  {
    files: [
      "**/__tests__/**/*",
      "**/*.test.{ts,tsx}",
      "**/*.spec.{ts,tsx}",
      "**/jest.setup.ts",
      "**/__mocks__/**/*",
      "**/mocks/**/*",
      "**/fixtures/**/*",
    ],
    rules: {
      // Allow 'any' type in tests - type safety less critical in test code
      "@typescript-eslint/no-explicit-any": "off",
      // Allow require() imports in tests (for dynamic mocking)
      "@typescript-eslint/no-require-imports": "off",
      // Allow unused vars in tests (test setup/fixtures)
      "@typescript-eslint/no-unused-vars": "off",
      // Relax exhaustive deps for test utilities
      "react-hooks/exhaustive-deps": "off",
    },
  },
  // Relaxed rules for API routes and app pages
  {
    files: ["**/app/**/*"],
    rules: {
      // App routes and pages often handle external data with unknown types
      "@typescript-eslint/no-explicit-any": "warn",
      // Request params not always used in GET handlers
      "@typescript-eslint/no-unused-vars": "warn",
    },
  },
  // Relaxed rules for chart components
  {
    files: ["**/components/**/*Chart*.{ts,tsx}", "**/components/**/Chart*.{ts,tsx}"],
    rules: {
      // Chart libraries like recharts often require 'any' for formatters and handlers
      "@typescript-eslint/no-explicit-any": "warn",
    },
  },
  // Relaxed rules for specific component patterns
  {
    files: ["**/components/**/*", "**/hooks/**/*"],
    rules: {
      // Allow some flexibility in hooks - warn instead of error
      "react-hooks/exhaustive-deps": "warn",
      "react-hooks/set-state-in-effect": "warn",
      "react-hooks/purity": "warn",
    },
  },
]);

export default eslintConfig;
