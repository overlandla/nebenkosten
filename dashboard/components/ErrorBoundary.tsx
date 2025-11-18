'use client';

import { Component, ReactNode } from 'react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
  errorInfo?: { componentStack: string };
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: { componentStack: string }) {
    console.error('ErrorBoundary caught an error:', error, errorInfo);
    this.setState({
      error,
      errorInfo,
    });
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="min-h-screen flex items-center justify-center bg-neutral-50 px-4">
          <div className="max-w-2xl w-full">
            <div className="bg-white rounded-lg shadow-lg border border-red-200 p-8">
              <div className="flex items-start space-x-4">
                <div className="flex-shrink-0">
                  <svg
                    className="h-12 w-12 text-red-500"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                    />
                  </svg>
                </div>
                <div className="flex-1">
                  <h1 className="text-2xl font-bold text-neutral-900 mb-2">
                    Something went wrong
                  </h1>
                  <p className="text-neutral-600 mb-4">
                    An unexpected error occurred. Please try refreshing the page.
                  </p>

                  {this.state.error && (
                    <div className="bg-red-50 rounded-lg p-4 mb-4">
                      <p className="text-sm font-semibold text-red-800 mb-2">
                        Error Details:
                      </p>
                      <pre className="text-xs text-red-700 overflow-x-auto">
                        {this.state.error.message}
                      </pre>
                    </div>
                  )}

                  {this.state.errorInfo && process.env.NODE_ENV === 'development' && (
                    <details className="bg-neutral-100 rounded-lg p-4 mb-4">
                      <summary className="text-sm font-semibold text-neutral-700 cursor-pointer">
                        Component Stack (Development Only)
                      </summary>
                      <pre className="text-xs text-neutral-600 mt-2 overflow-x-auto">
                        {this.state.errorInfo.componentStack}
                      </pre>
                    </details>
                  )}

                  <div className="flex space-x-3">
                    <button
                      onClick={() => window.location.reload()}
                      className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                    >
                      Reload Page
                    </button>
                    <button
                      onClick={() => window.location.href = '/'}
                      className="px-4 py-2 bg-neutral-600 text-white rounded-lg hover:bg-neutral-700 transition-colors"
                    >
                      Go to Home
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
