import { StatusBar } from 'expo-status-bar';
import { useEffect, useMemo, useRef, useState } from 'react';
import {
  Pressable,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { AdaptiveRenderer, type LayoutConfig } from './src/adaptive';
import { AnswersContext, answerLabel, type Answers } from './src/demo/answers';
import { optionSets } from './src/demo/capabilities';
import { fetchLayout, fetchPersonalizedLayout, putSession } from './src/demo/api';
import { layoutA } from './src/demo/layouts';
import { registry } from './src/demo/registry';
import { SessionContext } from './src/demo/session';
import {
  createSessionRecorder,
  type InteractionEvent,
  type LayoutSource,
} from './src/demo/sessionRecorder';

const recorder = createSessionRecorder(putSession);

/** The layout on screen, with the onboarding session that measures it. */
type Experience = {
  sessionId: string;
  source: LayoutSource;
  layout: LayoutConfig;
  /** Onboarding answers by option-set id: in memory only, never sent to the server. */
  answers: Answers;
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
    setExperience({ sessionId, source, layout, answers: {}, completed: false });
  }

  function loadInitial() {
    return fetchLayout()
      .then((layout) => show('static', layout))
      .catch(() => show('fallback', layoutA));
  }

  useEffect(() => {
    if (started.current) return;
    started.current = true;
    void loadInitial();
  }, []);

  /** Demo only: leave the congratulations screen and begin a fresh, separately measured session. */
  function startOver() {
    setExperience(null);
    setPreference('');
    setError(null);
    setGenerating(false);
    void loadInitial(); // starting a session also retries any unsent telemetry
  }

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

  const sessionId = experience?.sessionId;
  const completed = experience?.completed ?? false;
  // Everything the composed UI can do is bound to this one session id.
  const sessionValue = useMemo(
    () => ({
      completed,
      recordInteraction: (event: InteractionEvent) => {
        if (sessionId) recorder.recordInteraction(sessionId, event);
      },
      // The host decides what each approved action does. Completion telemetry is queued and
      // synced in the background: it never blocks, and a failed sync never reopens onboarding.
      runAction: (action: string) => {
        if (!sessionId || action !== 'complete_onboarding') return;
        recorder.complete(sessionId); // idempotent: keeps the first completion time
        setExperience((e) => (e && e.sessionId === sessionId ? { ...e, completed: true } : e));
      },
    }),
    [sessionId, completed],
  );

  // Bound to this session id, like the telemetry above: a stale tree can't touch a newer session.
  const answers = experience?.answers;
  const answersValue = useMemo(
    () => ({
      answers: answers ?? {},
      setAnswer: (optionSet: string, value: string) =>
        setExperience((e) =>
          e && e.sessionId === sessionId && !e.completed
            ? { ...e, answers: { ...e.answers, [optionSet]: value } }
            : e,
        ),
    }),
    [sessionId, answers],
  );

  if (experience?.completed) {
    // Option-set order comes from the manifest; unanswered sets are skipped.
    const summary = Object.keys(optionSets).filter((id) => experience.answers[id]);
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.congrats}>
          <Text style={styles.congratsTitle}>Congratulations!</Text>
          <Text style={styles.congratsText}>You're all set. Your personalized plan is ready.</Text>
          {summary.length > 0 && (
            <View style={styles.summary}>
              <Text style={styles.summaryTitle}>Your preferences</Text>
              {summary.map((id) => (
                <Text key={id} style={styles.summaryRow}>
                  {answerLabel(id)}: <Text style={styles.summaryValue}>{experience.answers[id]}</Text>
                </Text>
              ))}
            </View>
          )}
          <Pressable accessibilityRole="button" style={[styles.button, styles.centered]} onPress={startOver}>
            <Text style={styles.buttonText}>Start over</Text>
          </Pressable>
        </View>
        <StatusBar style="auto" />
      </SafeAreaView>
    );
  }

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
              <AnswersContext.Provider value={answersValue}>
                <AdaptiveRenderer layout={experience.layout} registry={registry} />
              </AnswersContext.Provider>
            </SessionContext.Provider>
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
  congrats: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: 24, gap: 12 },
  centered: { alignSelf: 'center' },
  summary: { alignSelf: 'stretch', maxWidth: 360, padding: 16, borderRadius: 12, backgroundColor: '#f4f4f5', gap: 6, marginBottom: 12 },
  summaryTitle: { fontSize: 16, fontWeight: '700', marginBottom: 4 },
  summaryRow: { fontSize: 16, color: '#444' },
  summaryValue: { fontWeight: '600', color: '#000' },
  congratsTitle: { fontSize: 32, fontWeight: '700' },
  congratsText: { fontSize: 18, color: '#444', textAlign: 'center', marginBottom: 12 },
  button: {
    marginVertical: 12,
    alignSelf: 'flex-start',
    minHeight: 44,
    justifyContent: 'center',
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
