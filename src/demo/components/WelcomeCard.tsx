import { StyleSheet, Text, View } from 'react-native';

type Props = {
  title: string;
  message: string;
};

export function WelcomeCard({ title, message }: Props) {
  return (
    <View style={styles.card}>
      <Text style={styles.title}>{title}</Text>
      <Text style={styles.message}>{message}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    flex: 1,
    padding: 20,
    borderRadius: 12,
    backgroundColor: '#e8f0fe',
  },
  title: { fontSize: 22, fontWeight: '700', marginBottom: 8 },
  message: { fontSize: 16, color: '#444' },
});
