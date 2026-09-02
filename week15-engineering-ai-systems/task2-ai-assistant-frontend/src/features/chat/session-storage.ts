import "client-only"

import type { ChatMessage, ChatSession } from "./types"

const STORAGE_KEY = "engineering-ai-assistant.sessions"
const STORAGE_VERSION = 1

export interface SessionState {
  sessions: ChatSession[]
  activeSessionId: string | null
}

interface StoredSessionState extends SessionState {
  version: typeof STORAGE_VERSION
}

export class SessionStorageError extends Error {
  constructor(message: string, options?: ErrorOptions) {
    super(message, options)
    this.name = "SessionStorageError"
  }
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
  const serializedState = storage.getItem(STORAGE_KEY)
  if (serializedState === null) {
    return createEmptySessionState()
  }

  try {
    const storedState: unknown = JSON.parse(serializedState)
    if (!isStoredSessionState(storedState)) {
      return createEmptySessionState()
    }

    return normalizeActiveSession(storedState)
  } catch {
    return createEmptySessionState()
  }
}

export function saveSessionState(
  state: SessionState,
  storage: Storage = window.localStorage
): void {
  if (!isSessionState(state)) {
    throw new SessionStorageError("Cannot save invalid chat session data")
  }

  const storedState: StoredSessionState = {
    version: STORAGE_VERSION,
    ...state,
  }

  try {
    storage.setItem(STORAGE_KEY, JSON.stringify(storedState))
  } catch (error) {
    throw new SessionStorageError("Could not save chat sessions", {
      cause: error,
    })
  }
}

export function clearSessionState(
  storage: Storage = window.localStorage
): void {
  storage.removeItem(STORAGE_KEY)
}

function normalizeActiveSession(state: StoredSessionState): SessionState {
  const activeSessionExists = state.sessions.some(
    (session) => session.id === state.activeSessionId
  )

  return {
    sessions: state.sessions,
    activeSessionId: activeSessionExists
      ? state.activeSessionId
      : (state.sessions[0]?.id ?? null),
  }
}

function isStoredSessionState(value: unknown): value is StoredSessionState {
  return (
    isRecord(value) &&
    value.version === STORAGE_VERSION &&
    isSessionState(value)
  )
}

function isSessionState(value: unknown): value is SessionState {
  return (
    isRecord(value) &&
    (value.activeSessionId === null ||
      typeof value.activeSessionId === "string") &&
    Array.isArray(value.sessions) &&
    value.sessions.every(isChatSession)
  )
}

function isChatSession(value: unknown): value is ChatSession {
  return (
    isRecord(value) &&
    typeof value.id === "string" &&
    typeof value.title === "string" &&
    typeof value.useRag === "boolean" &&
    typeof value.createdAt === "string" &&
    typeof value.updatedAt === "string" &&
    Array.isArray(value.documentIds) &&
    value.documentIds.every((id) => typeof id === "string") &&
    Array.isArray(value.messages) &&
    value.messages.every(isChatMessage)
  )
}

function isChatMessage(value: unknown): value is ChatMessage {
  if (
    !isRecord(value) ||
    typeof value.id !== "string" ||
    typeof value.content !== "string" ||
    typeof value.createdAt !== "string"
  ) {
    return false
  }

  if (value.role === "user") {
    return true
  }

  return value.role === "assistant" && isAssistantMessage(value)
}

function isAssistantMessage(value: Record<string, unknown>): boolean {
  return (
    (value.status === "streaming" ||
      value.status === "complete" ||
      value.status === "error") &&
    Array.isArray(value.sources) &&
    Array.isArray(value.tools)
  )
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null
}
