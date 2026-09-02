import "client-only"

import { API_BASE_URL, throwApiError } from "@/lib/api"

import type { ChatRequest, ChatStreamEvent } from "./types"

export async function streamChat(
  request: ChatRequest,
  onEvent: (event: ChatStreamEvent) => void,
  signal?: AbortSignal
): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
    signal,
  })

  if (!response.ok) {
    await throwApiError(response)
  }
  
  if (!response.body) {
    throw new Error("The streaming response has no body")
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ""

  while (true) {
    const { done, value } = await reader.read()
    buffer += decoder.decode(value, { stream: !done }).replaceAll("\r\n", "\n")

    const eventBlocks = buffer.split("\n\n")
    buffer = eventBlocks.pop() ?? ""

    for (const eventBlock of eventBlocks) {
      emitEvent(eventBlock, onEvent)
    }

    if (done) {
      if (buffer.trim()) {
        emitEvent(buffer, onEvent)
      }
      return
    }
  }
}

function emitEvent(
  eventBlock: string,
  onEvent: (event: ChatStreamEvent) => void
): void {
  const data = eventBlock
    .split("\n")
    .filter((line) => line.startsWith("data:"))
    .map((line) => line.slice(5).trimStart())
    .join("\n")

  if (!data) return
  onEvent(JSON.parse(data) as ChatStreamEvent)
}
