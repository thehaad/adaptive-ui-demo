import type { LayoutConfig } from '../adaptive';

const API_URL = process.env.EXPO_PUBLIC_API_URL ?? 'http://localhost:8000';

export async function fetchLayout(): Promise<LayoutConfig> {
  const response = await fetch(`${API_URL}/api/layout`);
  if (!response.ok) {
    throw new Error(`Layout request failed: ${response.status}`);
  }
  return response.json();
}
