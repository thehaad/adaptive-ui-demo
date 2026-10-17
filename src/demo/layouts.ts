import type { LayoutConfig } from '../adaptive';

const welcome = {
  component: 'WelcomeCard',
  props: { title: 'Welcome back', message: 'Pick what you want to see.' },
};

const preferences = {
  component: 'PreferenceSelector',
  props: { label: 'Interests', options: ['News', 'Sports', 'Music', 'Tech'] },
};

/** Layout A: always stacked vertically. */
export const layoutA: LayoutConfig = {
  id: 'A',
  root: {
    component: 'Row',
    props: { direction: 'column' },
    children: [welcome, preferences],
  },
};

/** Layout B: side by side on wide screens, stacked on narrow ones. */
export const layoutB: LayoutConfig = {
  id: 'B',
  root: {
    component: 'Row',
    props: { direction: 'row', breakpoint: 600 },
    children: [welcome, preferences],
  },
};
