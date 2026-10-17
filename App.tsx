import { StatusBar } from 'expo-status-bar';
import { useEffect, useMemo, useRef, useState } from 'react';
import {
  Pressable,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
} from 'react-native';
import { AdaptiveRenderer, type LayoutConfig } from './src/adaptive';
import { fetchLayout, fetchPersonalizedLayout, putSession } from './src/demo/api';
import { layoutA } from './src/demo/layouts';
import { registry } from './src/demo/registry';
import { SessionContext } from './src/demo/session';
import { createSessionRecorder, type LayoutSource } from './src/demo/sessionRecorder';

const recorder = createSessionRecorder(putSession);

/** The layout on screen, with the onboarding session that measures it. */
type Experience = {
  sessionId: string;
  source: LayoutSource;
  layout: LayoutConfig;
  completed: boolean;
};

export default function App() {
  const [experience, setExperience] = useState<Experience | null>(null);
  const [preference, setPreference] = useState('');
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const started = useRef(false);

  function show(source: LayoutSource, layout: LayoutConfig, pref: string | null = null) {
    const sessionId = recorder.startSession({ layoutSource: source, preference: pref, layout });
    setExperience({ sessionId, source, layout, completed: false });
  }

  useEffect(() => {
    if (started.current) return;
    started.current = true;
    fetchLayout()
      .then((layout) => show('static', layout))
      .catch(() => show('fallback', layoutA));
  }, []);

  async function personalize() {
    const text = preference.trim();
    setGenerating(true);
    setError(null);
    try {
      show('ai', await fetchPersonalizedLayout(text), text);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Something went wrong');
    } finally {
      setGenerating(false);
    }
  }

  function complete() {
    if (!experience) return;
    recorder.complete(experience.sessionId);
    setExperience({ ...experience, completed: true });
  }

  const sessionId = experience?.sessionId;
  const sessionValue = useMemo(
    () => ({ recordInteraction: () => sessionId && recorder.recordInteraction(sessionId) }),
    [sessionId],
  );

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
        <Text style={styles.hint}>Please don't include personal details.</Text>
        <Pressable
          style={[styles.button, (!experience || generating || !preference.trim()) && styles.disabled]}
          disabled={!experience || generating || !preference.trim()}
          onPress={personalize}
        >
          <Text style={styles.buttonText}>
            {generating ? 'Generating…' : 'Personalize'}
          </Text>
        </Pressable>
        {error && <Text style={styles.fallback}>{error}</Text>}

        {!experience && <Text style={styles.note}>Loading layout…</Text>}
        {experience && (
          <>
            {experience.source === 'fallback' && (
              <Text style={styles.fallback}>
                Server unavailable — showing local fallback (Layout {experience.layout.id})
              </Text>
            )}
            <Text style={styles.note}>
              Layout: {experience.layout.id} ({experience.source})
            </Text>
            <SessionContext.Provider key={experience.sessionId} value={sessionValue}>
              <AdaptiveRenderer layout={experience.layout} registry={registry} />
            </SessionContext.Provider>
            <Pressable
              style={[styles.button, experience.completed && styles.disabled]}
              disabled={experience.completed}
              onPress={complete}
            >
              <Text style={styles.buttonText}>
                {experience.completed ? 'Onboarding complete ✓' : 'Complete onboarding'}
              </Text>
            </Pressable>
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
  hint: { fontSize: 12, color: '#888', marginTop: 4 },
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
