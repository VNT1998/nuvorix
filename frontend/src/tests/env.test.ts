import { describe, it, expect } from 'vitest';
import { env } from '../lib/env';

describe('Environment Configuration', () => {
  it('provides default API url', () => {
    expect(env.apiUrl).toBeDefined();
    expect(typeof env.apiUrl).toBe('string');
  });

  it('provides default platform name', () => {
    expect(env.platformName).toBe('Nuvorix');
  });
});
