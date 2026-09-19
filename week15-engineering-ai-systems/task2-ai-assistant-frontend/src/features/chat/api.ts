import "client-only"

import { apiFetch, throwApiError } from "@/lib/api"

import type {
  ChatStreamEvent,
  SessionDetailDto,
  SessionSummaryDto,
} from "./types"

export async function listSessions(): Promise<SessionSummaryDto[]> {
  const response = await apiFetch("/sessions")
  if (!response.ok) await throwApiError(response)
  return (await response.json()) as SessionSummaryDto[]
}

export async function getSession(sessionId: string): Promise<SessionDetailDto> {
  const response = await apiFetch(`/sessions/${sessionId}`)
  if (!response.ok) await throwApiError(response)
  return (await response.json()) as SessionDetailDto
}

export async function createSession(): Promise<SessionSummaryDto> {
  const response = await apiFetch("/sessions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title: "New chat", use_rag: true }),
  })
  if (!response.ok) await throwApiError(response)
  return (await response.json()) as SessionSummaryDto
}

export async function updateSession(
  sessionId: string,
  changes: { title?: string; use_rag?: boolean }
): Promise<SessionSummaryDto> {
  const response = await apiFetch(`/sessions/${sessionId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(changes),
  })
  if (!response.ok) await throwApiError(response)
  return (await response.json()) as SessionSummaryDto
}

export async function deleteSession(sessionId: string): Promise<void> {
  const response = await apiFetch(`/sessions/${sessionId}`, {
    method: "DELETE",
  })
  if (!response.ok) await throwApiError(response)
}

interface StreamChatRequest {
  session_id: string
  message: string
  document_ids: string[]
}

const DELTA_CHARACTERS_PER_FRAME = 48

export async function streamChat(
  request: StreamChatRequest,
  onEvent: (event: ChatStreamEvent) => void,
  signal?: AbortSignal
): Promise<void> {
  const response = await apiFetch("/chat/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
    signal,
  })

  if (!response.ok) await throwApiError(response)
  if (!response.body) throw new Error("The streaming response has no body")
  await readEventStream(response.body, onEvent, signal)
}

async function readEventStream(
  body: ReadableStream<Uint8Array>,
  onEvent: (event: ChatStreamEvent) => void,
  signal?: AbortSignal
) {
  const reader = body.getReader()
  const decoder = new TextDecoder()
  let buffer = ""

  while (true) {
    const { done, value } = await reader.read()
    buffer += decoder.decode(value, { stream: !done }).replaceAll("\r\n", "\n")
    const blocks = buffer.split("\n\n")
    buffer = blocks.pop() ?? ""
    await emitEvents(blocks, onEvent, signal)

    if (done) {
      if (buffer.trim()) await emitEvents([buffer], onEvent, signal)
      return
    }
  }
}

async function emitEvents(
  blocks: string[],
  onEvent: (event: ChatStreamEvent) => void,
  signal?: AbortSignal
) {
  let pendingText = ""

  for (const block of blocks) {
    const event = parseEvent(block)
    if (!event) continue

    // Step 1: Combine provider deltas that arrived in one network chunk.
    if (event.type === "delta") {
      pendingText += event.content
      continue
    }

    // Step 2: Render queued text before later tool or completion events.
    await emitTextProgressively(pendingText, onEvent, signal)
    pendingText = ""

    // Step 3: Emit non-text events in their original order.
    throwIfAborted(signal)
    onEvent(event)
    await waitForPaint()
  }

  await emitTextProgressively(pendingText, onEvent, signal)
}

function parseEvent(eventBlock: string): ChatStreamEvent | null {
  const data = eventBlock
    .split("\n")
    .filter((line) => line.startsWith("data:"))
    .map((line) => line.slice(5).trimStart())
    .join("\n")

  return data ? (JSON.parse(data) as ChatStreamEvent) : null
}

async function emitTextProgressively(
  content: string,
  onEvent: (event: ChatStreamEvent) => void,
  signal?: AbortSignal
) {
  for (
    let start = 0;
    start < content.length;
    start += DELTA_CHARACTERS_PER_FRAME
  ) {
    throwIfAborted(signal)
    onEvent({
      type: "delta",
      content: content.slice(start, start + DELTA_CHARACTERS_PER_FRAME),
    })
    await waitForPaint()
  }
}

function waitForPaint(): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, 16))
}

function throwIfAborted(signal?: AbortSignal) {
  if (signal?.aborted) {
    throw new DOMException("The request was stopped", "AbortError")
  }
}
