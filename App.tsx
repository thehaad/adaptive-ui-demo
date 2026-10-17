import { StatusBar } from 'expo-status-bar';
import { useEffect, useState } from 'react';
import { SafeAreaView, StyleSheet, Text } from 'react-native';
import { AdaptiveRenderer, type LayoutConfig } from './src/adaptive';
import { fetchLayout } from './src/demo/api';
import { layoutA } from './src/demo/layouts';
import { registry } from './src/demo/registry';

type State =
  | { status: 'loading' }
  | { status: 'server'; layout: LayoutConfig }
  | { status: 'fallback' };

export default function App() {
  const [state, setState] = useState<State>({ status: 'loading' });

  useEffect(() => {
    fetchLayout()
      .then((layout) => setState({ status: 'server', layout }))
      .catch(() => setState({ status: 'fallback' }));
  }, []);

  return (
    <SafeAreaView style={styles.container}>
      {state.status === 'loading' && <Text style={styles.note}>Loading layout…</Text>}
      {state.status === 'server' && (
        <>
          <Text style={styles.note}>Layout: {state.layout.id} (from server)</Text>
          <AdaptiveRenderer layout={state.layout} registry={registry} />
        </>
      )}
      {state.status === 'fallback' && (
        <>
          <Text style={styles.fallback}>
            Server unavailable — showing local fallback (Layout {layoutA.id})
          </Text>
          <AdaptiveRenderer layout={layoutA} registry={registry} />
        </>
      )}
      <StatusBar style="auto" />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 24, paddingTop: 64, backgroundColor: '#fff' },
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
