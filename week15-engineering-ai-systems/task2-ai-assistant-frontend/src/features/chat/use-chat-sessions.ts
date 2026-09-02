"use client"

import { useEffect, useRef, useState } from "react"

import { streamChat } from "./api"
import {
  createEmptySessionState,
  loadSessionState,
  saveSessionState,
  type SessionState,
} from "./session-storage"
import type {
  AssistantMessage,
  ChatHistoryMessage,
  MessageAttachment,
  ChatSession,
  ChatStreamEvent,
  UserMessage,
} from "./types"

export function useChatSessions() {
  const [state, setState] = useState<SessionState>(createEmptySessionState)
  const activeRequest = useRef<AbortController | null>(null)

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

  async function sendMessage(
    content: string,
    attachments: MessageAttachment[] = []
  ) {
    const cleanContent = content.trim()
    if (!cleanContent || activeRequest.current) return

    const requestController = new AbortController()
    activeRequest.current = requestController

    // Step 1: Build the user and pending assistant messages.
    const now = new Date().toISOString()
    const userMessage: UserMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: cleanContent,
      createdAt: now,
      attachments,
    }
    const assistantMessage: AssistantMessage = {
      id: crypto.randomUUID(),
      role: "assistant",
      content: "",
      createdAt: now,
      status: "streaming",
      activity: "Starting",
      activities: ["Started request"],
      followUpQuestions: [],
      sources: [],
      tools: [],
    }

    // Step 2: Add both messages to the active session or a new session.
    const session = activeSession ?? buildSession()
    const updatedSession: ChatSession = {
      ...session,
      title:
        session.messages.length === 0
          ? createSessionTitle(cleanContent)
          : session.title,
      messages: [...session.messages, userMessage, assistantMessage],
      updatedAt: now,
    }

    const otherSessions = state.sessions.filter(
      (existingSession) => existingSession.id !== updatedSession.id
    )
    const updatedState: SessionState = {
      sessions: [updatedSession, ...otherSessions],
      activeSessionId: updatedSession.id,
    }

    setState(updatedState)
    saveSessionState(updatedState)

    // Step 3: Send previous messages as conversation history.
    const history: ChatHistoryMessage[] = session.messages
      .filter((message) => message.content.trim())
      .map((message) => ({
        role: message.role,
        content: message.content,
      }))
      .slice(-20)

    try {
      await streamChat(
        {
          message: cleanContent,
          history,
          use_rag: session.useRag,
        },
        (event) =>
          handleStreamEvent(updatedSession.id, assistantMessage.id, event),
        requestController.signal
      )
    } catch {
      if (requestController.signal.aborted) {
        markAssistantStopped(updatedSession.id, assistantMessage.id)
        return
      }

      markAssistantError(
        updatedSession.id,
        assistantMessage.id,
        "Could not reach the assistant. Please try again."
      )
    } finally {
      if (activeRequest.current === requestController) {
        activeRequest.current = null
      }
    }
  }

  function stopGeneration() {
    activeRequest.current?.abort()
  }

  function handleStreamEvent(
    sessionId: string,
    messageId: string,
    event: ChatStreamEvent
  ) {
    if (event.type === "status") {
      updateAssistantMessage(sessionId, messageId, (message) => ({
        ...message,
        activity: event.message,
        activities:
          message.activities?.at(-1) === event.message
            ? message.activities
            : [...(message.activities ?? []), event.message],
      }))
    }

    if (event.type === "tool") {
      updateAssistantMessage(sessionId, messageId, (message) => ({
        ...message,
        tools: [...message.tools, event.tool],
      }))
    }

    if (event.type === "delta") {
      updateAssistantMessage(sessionId, messageId, (message) => ({
        ...message,
        content: message.content + event.content,
      }))
    }

    if (event.type === "complete") {
      updateAssistantMessage(
        sessionId,
        messageId,
        (message) => ({
          ...message,
          content: event.response.answer,
          status: "complete",
          confidence: event.response.confidence,
          followUpQuestions: event.response.follow_up_questions,
          sources: event.response.sources,
          tools: event.response.tools_used,
          model: event.response.model,
          usedFallback: event.response.used_fallback,
        }),
        true
      )
    }

    if (event.type === "error") {
      markAssistantError(sessionId, messageId, event.message)
    }
  }

  function markAssistantError(
    sessionId: string,
    messageId: string,
    errorMessage: string
  ) {
    updateAssistantMessage(
      sessionId,
      messageId,
      (message) => ({
        ...message,
        content: message.content || errorMessage,
        status: "error",
        activity: undefined,
      }),
      true
    )
  }

  function markAssistantStopped(sessionId: string, messageId: string) {
    updateAssistantMessage(
      sessionId,
      messageId,
      (message) => ({
        ...message,
        content: message.content || "Response stopped.",
        status: "complete",
        activity: undefined,
      }),
      true
    )
  }

  function updateAssistantMessage(
    sessionId: string,
    messageId: string,
    update: (message: AssistantMessage) => AssistantMessage,
    persist = false
  ) {
    setState((currentState) => {
      const updatedSessions = currentState.sessions.map((session) => {
        if (session.id !== sessionId) return session

        const updatedMessages = session.messages.map((message) => {
          if (message.id !== messageId || message.role !== "assistant") {
            return message
          }
          return update(message)
        })

        return {
          ...session,
          messages: updatedMessages,
          updatedAt: new Date().toISOString(),
        }
      })

      const updatedState: SessionState = {
        ...currentState,
        sessions: updatedSessions,
      }

      if (persist) {
        saveSessionState(updatedState)
      }
      return updatedState
    })
  }

  return {
    sessions: state.sessions,
    activeSession,
    activeSessionId: state.activeSessionId,
    createSession,
    selectSession,
    renameSession,
    deleteSession,
    sendMessage,
    stopGeneration,
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
