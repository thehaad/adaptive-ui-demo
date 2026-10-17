import { useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

type Props = {
  label: string;
  options: string[];
};

export function PreferenceSelector({ label, options }: Props) {
  const [selected, setSelected] = useState<string | null>(null);

  return (
    <View style={styles.container}>
      <Text style={styles.label}>{label}</Text>
      <View style={styles.options}>
        {options.map((option) => (
          <Pressable
            key={option}
            onPress={() => setSelected(option)}
            style={[styles.chip, selected === option && styles.chipSelected]}
          >
            <Text style={selected === option && styles.chipTextSelected}>
              {option}
            </Text>
          </Pressable>
        ))}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 20,
    borderRadius: 12,
    backgroundColor: '#f4f4f5',
  },
  label: { fontSize: 18, fontWeight: '600', marginBottom: 12 },
  options: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  chip: {
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 999,
    borderWidth: 1,
    borderColor: '#bbb',
    backgroundColor: '#fff',
  },
  chipSelected: { backgroundColor: '#1a73e8', borderColor: '#1a73e8' },
  chipTextSelected: { color: '#fff' },
});
