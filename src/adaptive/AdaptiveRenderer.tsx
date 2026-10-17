import type { ReactElement } from 'react';
import type { ComponentRegistry, LayoutConfig, LayoutNode } from './types';

type Props = {
  layout: LayoutConfig;
  registry: ComponentRegistry;
};

function renderNode(
  node: LayoutNode,
  registry: ComponentRegistry,
  key?: number,
): ReactElement {
  const Component = registry[node.component];
  if (!Component) {
    throw new Error(
      `AdaptiveRenderer: unknown component "${node.component}". ` +
        `Registered components: ${Object.keys(registry).join(', ') || '(none)'}.`,
    );
  }
  return (
    <Component key={key} {...node.props}>
      {node.children?.map((child, i) => renderNode(child, registry, i))}
    </Component>
  );
}

export function AdaptiveRenderer({ layout, registry }: Props) {
  return renderNode(layout.root, registry);
}
