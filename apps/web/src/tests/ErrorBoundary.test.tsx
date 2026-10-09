import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ErrorBoundary } from '../components/ErrorBoundary';

const FaultyComponent: React.FC = () => {
  throw new Error('Explosion in render cycle');
};

describe('ErrorBoundary Component', () => {
  it('renders children when no error occurs', () => {
    render(
      <ErrorBoundary>
        <div>Normal content</div>
      </ErrorBoundary>
    );

    expect(screen.getByText('Normal content')).toBeInTheDocument();
  });

  it('catches render errors and displays fallback UI', () => {
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {});

    render(
      <ErrorBoundary fallbackTitle="Custom View Failure">
        <FaultyComponent />
      </ErrorBoundary>
    );

    expect(screen.getByText('Custom View Failure')).toBeInTheDocument();
    expect(screen.getByText('Explosion in render cycle')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /reload view/i })).toBeInTheDocument();

    spy.mockRestore();
  });
});
