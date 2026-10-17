import { useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { optionSets } from '../capabilities';
import { MIN_TARGET, metrics, useDensity } from '../density';
import { useSession } from '../session';

type Props = {
  label: string;
  optionSet: string;
};

export function PreferenceSelector({ label, optionSet }: Props) {
  const [selected, setSelected] = useState<string | null>(null);
  const { recordInteraction } = useSession();
  const m = metrics[useDensity()];
  const options = optionSets[optionSet]?.options;
  if (!options) {
    throw new Error(
      `PreferenceSelector: unknown optionSet "${optionSet}". ` +
        `Known: ${Object.keys(optionSets).join(', ')}.`,
    );
  }

  return (
    <View style={[styles.container, { padding: m.padding }]}>
      <Text style={[styles.label, { fontSize: m.label }]}>{label}</Text>
      <View style={[styles.options, { gap: m.chipGap }]}>
        {options.map((option) => (
          <Pressable
            key={option}
            accessibilityRole="button"
            accessibilityState={{ selected: selected === option }}
            onPress={() => {
              if (option === selected) return; // only a real change counts
              setSelected(option);
              recordInteraction('selection_changed');
            }}
            style={[
              styles.chip,
              { paddingHorizontal: m.chipPadding },
              selected === option && styles.chipSelected,
            ]}
          >
            <Text style={[{ fontSize: m.chipText }, selected === option && styles.chipTextSelected]}>
              {option}
            </Text>
          </Pressable>
        ))}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flexGrow: 1, borderRadius: 12, backgroundColor: '#f4f4f5' },
  label: { fontWeight: '600', marginBottom: 10 },
  options: { flexDirection: 'row', flexWrap: 'wrap' },
  chip: {
    minHeight: MIN_TARGET,
    minWidth: MIN_TARGET,
    justifyContent: 'center',
    alignItems: 'center',
    borderRadius: 999,
    borderWidth: 1,
    borderColor: '#bbb',
    backgroundColor: '#fff',
  },
  chipSelected: { backgroundColor: '#1a73e8', borderColor: '#1a73e8' },
  chipTextSelected: { color: '#fff' },
});
