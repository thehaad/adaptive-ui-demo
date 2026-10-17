import { Children, type ReactNode } from 'react';
import { StyleSheet, View, useWindowDimensions } from 'react-native';
import { DensityContext, metrics, type Density } from '../density';
import { isActionButton } from './ActionButton';

type Props = {
  /** "row" lays children out horizontally when the screen is wide enough. */
  direction?: 'row' | 'column';
  /** Screen width (px) below which a "row" collapses into a column. */
  breakpoint?: number;
  density?: Density;
  children?: ReactNode;
};

export function Row({ direction = 'row', breakpoint = 600, density = 'comfortable', children }: Props) {
  const { width } = useWindowDimensions();
  const horizontal = direction === 'row' && width >= breakpoint;
  const { gap } = metrics[density];
  // A trailing ActionButton is a footer: always below the controls, never beside them.
  const items = Children.toArray(children);
  let split = items.length;
  while (split > 0 && isActionButton(items[split - 1])) split--;

  return (
    <DensityContext.Provider value={density}>
      <View style={[styles.base, { gap }]}>
        <View style={[styles.controls, { gap, flexDirection: horizontal ? 'row' : 'column' }]}>
          {items.slice(0, split).map((child, i) => (
            <View key={i} style={horizontal ? styles.cell : styles.stackedCell}>
              {child}
            </View>
          ))}
        </View>
        {items.slice(split)}
      </View>
    </DensityContext.Provider>
  );
}

const styles = StyleSheet.create({
  base: { width: '100%' },
  controls: { width: '100%', flexWrap: 'wrap' },
  // Side by side: cells share the line and wrap if they get narrower than ~240px.
  cell: { flexGrow: 1, flexShrink: 1, flexBasis: 240 },
  stackedCell: { width: '100%' },
});
