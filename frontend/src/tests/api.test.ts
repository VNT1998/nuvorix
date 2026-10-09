import { describe, it, expect, vi, beforeEach } from 'vitest';
import { api } from '../lib/api';

describe('ApiClient', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('manages active user role', () => {
    api.setRole('ml_engineer');
    expect(api.getRole()).toBe('ml_engineer');

    api.setRole('admin');
    expect(api.getRole()).toBe('admin');
  });

  it('fetches projects with appropriate headers', async () => {
    const mockProjects = [
      { id: 'proj-1', name: 'Demo Project', description: '', created_at: '2026-10-09T00:00:00Z' },
    ];

    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => mockProjects,
    } as Response);

    const projs = await api.getProjects();
    expect(projs).toEqual(mockProjects);
    expect(fetchSpy).toHaveBeenCalledWith('/api/v1/projects', expect.anything());
  });

  it('handles error responses gracefully', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: false,
      status: 400,
      json: async () => ({ detail: 'Release evaluation gate blocked deployment' }),
    } as Response);

    await expect(api.createDeployment('w-1', 'v1.0.0', 'production', 'canary')).rejects.toThrow(
      'Release evaluation gate blocked deployment'
    );
  });
});
