"use client"

import { useEffect, useState } from "react"

import {
  createEmptySessionState,
  loadSessionState,
  saveSessionState,
  type SessionState,
} from "./session-storage"
import type { ChatSession } from "./types"

export function useChatSessions() {
  const [state, setState] = useState<SessionState>(createEmptySessionState)

  useEffect(() => {
    // Local storage is only available after the page loads in the browser.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setState(loadSessionState())
  }, [])

  const activeSession =
    state.sessions.find((session) => session.id === state.activeSessionId) ??
    null

  function createSession() {
    // Step 1: Create a blank chat session.
    const newSession = buildSession()

    // Step 2: Add it to the list and make it active.
    const updatedState: SessionState = {
      sessions: [newSession, ...state.sessions],
      activeSessionId: newSession.id,
    }

    // Step 3: Update the page and save the session locally.
    setState(updatedState)
    saveSessionState(updatedState)
  }

  function selectSession(sessionId: string) {
    // Ignore IDs that do not belong to an existing session.
    const sessionExists = state.sessions.some(
      (session) => session.id === sessionId
    )
    if (!sessionExists) return

    const updatedState: SessionState = {
      ...state,
      activeSessionId: sessionId,
    }

    setState(updatedState)
    saveSessionState(updatedState)
  }

  function renameSession(sessionId: string, title: string) {
    // Do not replace a useful title with empty text.
    const cleanTitle = title.trim()
    if (!cleanTitle) return

    const updatedSessions = state.sessions.map((session) =>
      session.id === sessionId
        ? {
            ...session,
            title: cleanTitle,
            updatedAt: new Date().toISOString(),
          }
        : session
    )

    const updatedState: SessionState = {
      ...state,
      sessions: updatedSessions,
    }

    setState(updatedState)
    saveSessionState(updatedState)
  }

  function deleteSession(sessionId: string) {
    // Step 1: Remove the selected session.
    const remainingSessions = state.sessions.filter(
      (session) => session.id !== sessionId
    )

    // Step 2: If it was active, select the next available session.
    const nextActiveSessionId =
      state.activeSessionId === sessionId
        ? (remainingSessions[0]?.id ?? null)
        : state.activeSessionId

    const updatedState: SessionState = {
      sessions: remainingSessions,
      activeSessionId: nextActiveSessionId,
    }

    // Step 3: Update the page and local storage.
    setState(updatedState)
    saveSessionState(updatedState)
  }

  return {
    sessions: state.sessions,
    activeSession,
    activeSessionId: state.activeSessionId,
    createSession,
    selectSession,
    renameSession,
    deleteSession,
  }
}

function buildSession(): ChatSession {
  const now = new Date().toISOString()

  return {
    id: crypto.randomUUID(),
    title: "New chat",
    messages: [],
    documentIds: [],
    useRag: true,
    createdAt: now,
    updatedAt: now,
  }
}
