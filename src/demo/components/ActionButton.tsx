import type { ReactNode } from 'react';
import { isValidElement } from 'react';
import { Pressable, StyleSheet, Text } from 'react-native';
import { actions } from '../capabilities';
import { MIN_TARGET, metrics, useDensity } from '../density';
import { useSession } from '../session';

type Props = {
  label: string;
  /** Id of a host-approved action from the capability manifest. */
  action: string;
};

/** True for an ActionButton element; containers use it to render the completion footer. */
export const isActionButton = (node: ReactNode) => isValidElement(node) && node.type === ActionButton;

export function ActionButton({ label, action }: Props) {
  const { runAction, completed } = useSession();
  const m = metrics[useDensity()];
  if (!(action in actions)) {
    throw new Error(
      `ActionButton: unknown action "${action}". Known: ${Object.keys(actions).join(', ')}.`,
    );
  }

  return (
    <Pressable
      accessibilityRole="button"
      disabled={completed}
      onPress={() => runAction(action)}
      style={[styles.button, { paddingHorizontal: m.chipPadding }]}
    >
      <Text style={[styles.text, { fontSize: m.chipText }]}>{label}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  button: {
    minHeight: MIN_TARGET,
    minWidth: MIN_TARGET,
    justifyContent: 'center',
    alignItems: 'center',
    alignSelf: 'flex-start',
    borderRadius: 10,
    backgroundColor: '#1a73e8',
  },
  text: { color: '#fff', fontWeight: '600' },
});
