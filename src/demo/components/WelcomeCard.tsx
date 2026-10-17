import { StyleSheet, Text, View } from 'react-native';
import { metrics, useDensity } from '../density';

type Props = {
  title: string;
  message: string;
};

export function WelcomeCard({ title, message }: Props) {
  const m = metrics[useDensity()];

  return (
    <View style={[styles.card, { padding: m.padding }]}>
      <Text style={[styles.title, { fontSize: m.title }]}>{title}</Text>
      <Text style={[styles.message, { fontSize: m.body }]}>{message}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  card: { flexGrow: 1, borderRadius: 12, backgroundColor: '#e8f0fe' },
  title: { fontWeight: '700', marginBottom: 6 },
  message: { color: '#444' },
});
