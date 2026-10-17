import { createContext, useContext } from 'react';

type SessionContextValue = { recordInteraction: () => void };

/** Lets host components report interactions for the session they are rendered in. */
export const SessionContext = createContext<SessionContextValue>({
  recordInteraction: () => {},
});

export const useSession = () => useContext(SessionContext);
