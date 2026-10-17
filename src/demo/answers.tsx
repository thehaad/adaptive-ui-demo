import { createContext, useContext } from 'react';

/** Onboarding answers keyed by the developer-defined option-set id. Not telemetry. */
export type Answers = Record<string, string>;

type AnswersContextValue = {
  answers: Answers;
  setAnswer: (optionSet: string, value: string) => void;
};

/** Host-owned answers for the current experience; kept in memory only. */
export const AnswersContext = createContext<AnswersContextValue>({
  answers: {},
  setAnswer: () => {},
});

export const useAnswers = () => useContext(AnswersContext);

/** "workout_location" -> "Workout location" */
export const answerLabel = (optionSet: string) => {
  const text = optionSet.replace(/_/g, ' ');
  return text.charAt(0).toUpperCase() + text.slice(1);
};
