"use client"

import { useEffect, useState } from "react"

import {
  createEmptySessionState,
  loadSessionState,
  saveSessionState,
  type SessionState,
} from "./session-storage"
import type { ChatSession, UserMessage } from "./types"

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

  function addUserMessage(content: string) {
    const cleanContent = content.trim()
    if (!cleanContent) return

    // Step 1: Build the user message.
    const now = new Date().toISOString()
    const newMessage: UserMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: cleanContent,
      createdAt: now,
    }

    // Step 2: Add it to the active session.
    if (activeSession) {
      const updatedSession: ChatSession = {
        ...activeSession,
        title:
          activeSession.messages.length === 0
            ? createSessionTitle(cleanContent)
            : activeSession.title,
        messages: [...activeSession.messages, newMessage],
        updatedAt: now,
      }

      const updatedSessions = state.sessions.map((session) =>
        session.id === updatedSession.id ? updatedSession : session
      )

      const updatedState: SessionState = {
        sessions: updatedSessions,
        activeSessionId: updatedSession.id,
      }

      setState(updatedState)
      saveSessionState(updatedState)
      return
    }

    // Step 3: If no session exists, create one with the message.
    const newSession: ChatSession = {
      ...buildSession(),
      title: createSessionTitle(cleanContent),
      messages: [newMessage],
      updatedAt: now,
    }

    const updatedState: SessionState = {
      sessions: [newSession, ...state.sessions],
      activeSessionId: newSession.id,
    }

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
    addUserMessage,
  }
}

function createSessionTitle(message: string): string {
  const maximumLength = 40

  return message.length > maximumLength
    ? `${message.slice(0, maximumLength)}…`
    : message
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
