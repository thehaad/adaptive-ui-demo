import { StatusBar } from 'expo-status-bar';
import { useEffect, useState } from 'react';
import {
  Pressable,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
} from 'react-native';
import { AdaptiveRenderer, type LayoutConfig } from './src/adaptive';
import { fetchLayout, fetchPersonalizedLayout } from './src/demo/api';
import { layoutA } from './src/demo/layouts';
import { registry } from './src/demo/registry';

type State =
  | { status: 'loading' }
  | { status: 'server'; layout: LayoutConfig }
  | { status: 'fallback' };

export default function App() {
  const [state, setState] = useState<State>({ status: 'loading' });
  const [preference, setPreference] = useState('');
  const [personalized, setPersonalized] = useState<LayoutConfig | null>(null);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchLayout()
      .then((layout) => setState({ status: 'server', layout }))
      .catch(() => setState({ status: 'fallback' }));
  }, []);

  async function personalize() {
    setGenerating(true);
    setError(null);
    try {
      setPersonalized(await fetchPersonalizedLayout(preference.trim()));
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Something went wrong');
    } finally {
      setGenerating(false);
    }
  }

  const layout =
    personalized ?? (state.status === 'server' ? state.layout : layoutA);

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.content}>
        <TextInput
          style={styles.input}
          value={preference}
          onChangeText={setPreference}
          placeholder="Describe your fitness goals, e.g. “I'm a beginner who wants short home workouts”"
          maxLength={500}
        />
        <Pressable
          style={[styles.button, (generating || !preference.trim()) && styles.disabled]}
          disabled={generating || !preference.trim()}
          onPress={personalize}
        >
          <Text style={styles.buttonText}>
            {generating ? 'Generating…' : 'Personalize'}
          </Text>
        </Pressable>
        {error && <Text style={styles.fallback}>{error}</Text>}

        {state.status === 'loading' && (
          <Text style={styles.note}>Loading layout…</Text>
        )}
        {state.status === 'fallback' && !personalized && (
          <Text style={styles.fallback}>
            Server unavailable — showing local fallback (Layout {layoutA.id})
          </Text>
        )}
        {state.status !== 'loading' && (
          <>
            <Text style={styles.note}>
              Layout: {layout.id}
              {personalized ? ' (AI-generated)' : state.status === 'server' ? ' (from server)' : ''}
            </Text>
            <AdaptiveRenderer layout={layout} registry={registry} />
          </>
        )}
      </ScrollView>
      <StatusBar style="auto" />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fff' },
  content: { padding: 24, paddingTop: 64 },
  input: {
    borderWidth: 1,
    borderColor: '#bbb',
    borderRadius: 8,
    padding: 12,
    fontSize: 16,
  },
  button: {
    marginVertical: 12,
    alignSelf: 'flex-start',
    paddingHorizontal: 20,
    paddingVertical: 12,
    borderRadius: 8,
    backgroundColor: '#1a73e8',
  },
  disabled: { opacity: 0.5 },
  buttonText: { color: '#fff', fontWeight: '600' },
  note: { fontSize: 14, color: '#888', marginBottom: 12 },
  fallback: {
    fontSize: 14,
    color: '#b3261e',
    backgroundColor: '#fdecea',
    padding: 8,
    borderRadius: 6,
    marginBottom: 12,
  },
});
