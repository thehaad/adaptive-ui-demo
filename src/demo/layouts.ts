import type { LayoutConfig } from '../adaptive';

const welcome = {
  component: 'WelcomeCard',
  props: {
    title: 'Ready to move?',
    message: "Tell us how you like to train and we'll shape your plan.",
  },
};

const preferences = {
  component: 'PreferenceSelector',
  props: {
    label: 'Workout focus',
    options: ['Strength', 'Cardio', 'Mobility', 'Recovery'],
  },
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
