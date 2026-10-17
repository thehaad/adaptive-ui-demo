import type { ReactNode } from 'react';
import { StyleSheet, View, useWindowDimensions } from 'react-native';

type Props = {
  /** "row" lays children out horizontally when the screen is wide enough. */
  direction?: 'row' | 'column';
  /** Screen width (px) below which a "row" collapses into a column. */
  breakpoint?: number;
  children?: ReactNode;
};

export function Row({ direction = 'row', breakpoint = 600, children }: Props) {
  const { width } = useWindowDimensions();
  const horizontal = direction === 'row' && width >= breakpoint;

  return (
    <View style={[styles.base, { flexDirection: horizontal ? 'row' : 'column' }]}>
      {children}
    </View>
  );
}

const styles = StyleSheet.create({
  base: { gap: 16, width: '100%' },
});
