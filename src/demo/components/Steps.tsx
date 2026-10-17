import { Children, useRef, useState, type ReactNode } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { DensityContext, MIN_TARGET, metrics, type Density } from '../density';
import { useSession } from '../session';
import { isActionButton } from './ActionButton';

type Props = {
  density?: Density;
  children?: ReactNode;
};

/**
 * Shows one child at a time, with progress and Back/Next. A trailing ActionButton is not a
 * step: it is the completion footer, shown beside Back on the last step.
 */
export function Steps({ density = 'comfortable', children }: Props) {
  const items = Children.toArray(children);
  const last = items[items.length - 1];
  const footer = isActionButton(last) ? last : null;
  const steps = footer ? items.slice(0, -1) : items;

  const [index, setIndex] = useState(0);
  const indexRef = useRef(0); // latest step, so a fast double tap can't count twice
  const { recordInteraction } = useSession();
  const m = metrics[density];
  const isLast = index === steps.length - 1;

  function go(delta: 1 | -1) {
    const next = Math.min(Math.max(indexRef.current + delta, 0), steps.length - 1);
    if (next === indexRef.current) return; // only a real step change counts
    indexRef.current = next;
    setIndex(next);
    recordInteraction(delta === 1 ? 'navigation_next' : 'navigation_back');
  }

  return (
    <DensityContext.Provider value={density}>
      <View style={[styles.container, { gap: m.gap }]}>
        <View style={{ gap: 6 }}>
          <Text style={[styles.progressText, { fontSize: m.body }]}>
            Step {index + 1} of {steps.length}
          </Text>
          <View style={styles.progressTrack}>
            {steps.map((_, i) => (
              <View key={i} style={[styles.progressSegment, i <= index && styles.progressDone]} />
            ))}
          </View>
        </View>

        {/* All steps stay mounted so earlier answers survive Back/Next. */}
        {steps.map((step, i) => (
          <View key={i} style={i === index ? undefined : styles.hidden}>
            {step}
          </View>
        ))}

        <View style={styles.nav}>
          {index > 0 ? (
            <Pressable accessibilityRole="button" onPress={() => go(-1)} style={[styles.navButton, styles.back]}>
              <Text style={[styles.backText, { fontSize: m.chipText }]}>Back</Text>
            </Pressable>
          ) : (
            <View style={styles.navButton} />
          )}
          {!isLast && (
            <Pressable accessibilityRole="button" onPress={() => go(1)} style={[styles.navButton, styles.next]}>
              <Text style={[styles.nextText, { fontSize: m.chipText }]}>Next</Text>
            </Pressable>
          )}
          {isLast && footer}
        </View>
      </View>
    </DensityContext.Provider>
  );
}

const styles = StyleSheet.create({
  container: { width: '100%', maxWidth: 560, alignSelf: 'center' },
  hidden: { display: 'none' },
  progressText: { color: '#555', fontWeight: '600' },
  progressTrack: { flexDirection: 'row', gap: 6 },
  progressSegment: { flex: 1, height: 6, borderRadius: 3, backgroundColor: '#d9dbe0' },
  progressDone: { backgroundColor: '#1a73e8' },
  nav: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: 12 },
  navButton: {
    minHeight: MIN_TARGET,
    minWidth: 96,
    justifyContent: 'center',
    alignItems: 'center',
    borderRadius: 10,
  },
  back: { borderWidth: 1, borderColor: '#bbb', backgroundColor: '#fff' },
  backText: { color: '#333', fontWeight: '600' },
  next: { backgroundColor: '#1a73e8' },
  nextText: { color: '#fff', fontWeight: '600' },
});
