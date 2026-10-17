import { createContext, useContext } from 'react';

export type Density = 'comfortable' | 'compact';

/** Density chosen by the enclosing layout container, read by leaf components. */
export const DensityContext = createContext<Density>('comfortable');
export const useDensity = () => useContext(DensityContext);

/** Minimum touch target (points) in every density; compact only tightens spacing and type. */
export const MIN_TARGET = 44;

export const metrics = {
  comfortable: { padding: 24, gap: 20, chipGap: 12, title: 26, body: 17, label: 20, chipText: 17, chipPadding: 20 },
  compact: { padding: 12, gap: 10, chipGap: 8, title: 17, body: 14, label: 15, chipText: 14, chipPadding: 14 },
} as const;
