import type { LayoutConfig } from '../adaptive';

const API_URL = process.env.EXPO_PUBLIC_API_URL ?? 'http://localhost:8000';

export async function fetchLayout(): Promise<LayoutConfig> {
  const response = await fetch(`${API_URL}/api/layout`);
  if (!response.ok) {
    throw new Error(`Layout request failed: ${response.status}`);
  }
  return response.json();
}

export async function fetchPersonalizedLayout(
  preference: string,
): Promise<LayoutConfig> {
  const response = await fetch(`${API_URL}/api/layout/personalize`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ preference }),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? `Request failed: ${response.status}`);
  }
  return response.json();
}
