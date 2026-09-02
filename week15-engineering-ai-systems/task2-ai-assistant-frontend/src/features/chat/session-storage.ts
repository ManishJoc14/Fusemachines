import "client-only"

import type { ChatSession } from "./types"

const STORAGE_KEY = "engineering-ai-assistant.sessions"
const STORAGE_VERSION = 1

export interface SessionState {
  sessions: ChatSession[]
  activeSessionId: string | null
}

interface StoredSessionState {
  version: typeof STORAGE_VERSION
  sessions: ChatSession[]
  activeSessionId: string | null
}

export function createEmptySessionState(): SessionState {
  return {
    sessions: [],
    activeSessionId: null,
  }
}

export function loadSessionState(
  storage: Storage = window.localStorage
): SessionState {
  try {
    const savedValue = storage.getItem(STORAGE_KEY)
    if (!savedValue) {
      return createEmptySessionState()
    }

    const savedState = JSON.parse(savedValue) as StoredSessionState
    if (savedState.version !== STORAGE_VERSION) {
      return createEmptySessionState()
    }

    return {
      sessions: savedState.sessions ?? [],
      activeSessionId: savedState.activeSessionId ?? null,
    }
  } catch {
    return createEmptySessionState()
  }
}

export function saveSessionState(
  state: SessionState,
  storage: Storage = window.localStorage
): void {
  const valueToSave: StoredSessionState = {
    version: STORAGE_VERSION,
    ...state,
  }

  storage.setItem(STORAGE_KEY, JSON.stringify(valueToSave))
}
