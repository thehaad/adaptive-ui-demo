import type { ComponentType } from 'react';

export type LayoutNode = {
  /** Key of the component in the registry. */
  component: string;
  /** JSON-compatible props passed to the component. */
  props?: Record<string, unknown>;
  /** Nested nodes, rendered as the component's children. */
  children?: LayoutNode[];
};

export type LayoutConfig = {
  id: string;
  root: LayoutNode;
};

export type ComponentRegistry = Record<string, ComponentType<any>>;
