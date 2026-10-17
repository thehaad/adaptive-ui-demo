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
    label: 'Training place',
    optionSet: 'workout_location',
  },
};

const complete = {
  component: 'ActionButton',
  props: { label: 'Complete onboarding', action: 'complete_onboarding' },
};

/** Layout A: always stacked vertically. Used as the offline fallback. */
export const layoutA: LayoutConfig = {
  id: 'A',
  root: {
    component: 'Row',
    props: { direction: 'column', density: 'comfortable' },
    children: [welcome, preferences, complete],
  },
};

/** Layout B: side by side on wide screens, stacked on narrow ones. */
export const layoutB: LayoutConfig = {
  id: 'B',
  root: {
    component: 'Row',
    props: { direction: 'row', breakpoint: 600, density: 'comfortable' },
    children: [welcome, preferences, complete],
  },
};
