/**
 * Typed environment configuration with sensible local defaults.
 * Prevents undefined runtime references and ensures VITE_ prefixes are respected.
 */

interface ClientEnv {
  apiUrl: string;
  platformName: string;
  isProduction: boolean;
}

export const env: ClientEnv = {
  apiUrl: (import.meta.env.VITE_API_URL as string) || 'http://127.0.0.1:8000',
  platformName: (import.meta.env.VITE_PLATFORM_NAME as string) || 'Nuvorix',
  isProduction: import.meta.env.PROD ?? false,
};
