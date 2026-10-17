import { createContext, useContext } from 'react';
import type { InteractionEvent } from './sessionRecorder';

type SessionContextValue = {
  /** Report a user interaction for the session this UI belongs to. */
  recordInteraction: (event: InteractionEvent) => void;
  /** Run a host-approved action (see the "actions" list in capabilities.json). */
  runAction: (action: string) => void;
  completed: boolean;
};

/** Lets host components report interactions and trigger actions for their own session. */
export const SessionContext = createContext<SessionContextValue>({
  recordInteraction: () => {},
  runAction: () => {},
  completed: false,
});

export const useSession = () => useContext(SessionContext);
