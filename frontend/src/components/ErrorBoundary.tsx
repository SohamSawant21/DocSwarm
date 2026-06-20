"use client";

import React, { Component, ErrorInfo, ReactNode } from "react";

interface Props {
  children?: ReactNode;
  fallback?: ReactNode;
  onReset?: () => void;
  sectionName?: string;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    // Update state so the next render will show the fallback UI.
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error(`Uncaught error in ${this.props.sectionName || 'ErrorBoundary'}:`, error, errorInfo);
  }

  public handleReset = () => {
    this.setState({ hasError: false, error: null });
    if (this.props.onReset) {
      this.props.onReset();
    }
  };

  public render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="flex flex-col items-center justify-center p-6 text-center h-full w-full bg-surface">
          <div className="bg-surface-bright border border-surface-variant rounded-xl p-6 shadow-sm w-full max-w-sm flex flex-col items-center">
            <span className="material-symbols-outlined text-error text-[48px] mb-4">
              warning
            </span>
            <h2 className="text-lg font-semibold text-on-surface mb-2">
              {this.props.sectionName ? `${this.props.sectionName} Crashed` : "Something went wrong"}
            </h2>
            <p className="text-sm text-on-surface-variant mb-6">
              An unexpected error occurred while rendering this section.
            </p>
            {this.state.error && (
              <div className="bg-surface p-3 rounded text-left overflow-auto mb-6 border border-surface-variant max-h-32 w-full">
                <code className="text-[11px] text-error font-mono break-all">
                  {this.state.error.message}
                </code>
              </div>
            )}
            <div className="flex gap-3 w-full">
              <button
                onClick={this.handleReset}
                className="flex-1 bg-primary text-on-primary hover:bg-[#002d94] transition-colors px-4 py-2 rounded-md text-sm font-medium"
              >
                Try Again
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
