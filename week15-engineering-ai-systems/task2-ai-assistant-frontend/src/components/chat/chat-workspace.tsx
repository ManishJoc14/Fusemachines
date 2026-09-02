"use client"

import { useState, type FormEvent, type KeyboardEvent } from "react"
import Image from "next/image"
import { ArrowUp, Paperclip } from "lucide-react"

import assistantLogo from "@/app/icon1.png"
import { ChatMessage } from "@/components/chat/chat-message"
import {
  ChatContainerContent,
  ChatContainerRoot,
  ChatContainerScrollAnchor,
} from "@/components/ui/chat-container"
import {
  InputGroup,
  InputGroupAddon,
  InputGroupButton,
  InputGroupTextarea,
} from "@/components/ui/input-group"
import { Separator } from "@/components/ui/separator"
import { SidebarTrigger } from "@/components/ui/sidebar"
import type { ChatMessage as ChatMessageType } from "@/features/chat/types"

interface ChatWorkspaceProps {
  messages: ChatMessageType[]
  isStreaming: boolean
  sessionTitle?: string
  onSendMessage: (message: string) => void
}

export function ChatWorkspace({
  messages,
  isStreaming,
  sessionTitle,
  onSendMessage,
}: ChatWorkspaceProps) {
  const [message, setMessage] = useState("")

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!message.trim() || isStreaming) return

    onSendMessage(message)
    setMessage("")
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault()
      event.currentTarget.form?.requestSubmit()
    }
  }

  return (
    <section className="flex h-full min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
      <header className="flex h-14 shrink-0 items-center px-3 sm:px-4">
        <div className="flex min-w-0 items-center gap-2">
          <SidebarTrigger aria-label="Open chat sessions" />
          <Separator className="mt-2 mr-1 h-4" orientation="vertical" />
          <h1 className="truncate text-sm font-semibold">
            {sessionTitle ?? "AI Assistant"}
          </h1>
        </div>
      </header>

      <ChatContainerRoot className="min-h-0 flex-1 px-4">
        {messages.length === 0 ? (
          <div className="flex h-full w-full items-center justify-center">
            <div className="w-full max-w-3xl pb-20 text-center">
              <Image
                alt=""
                className="mx-auto size-10 rounded-full"
                height={40}
                priority
                src={assistantLogo}
                width={40}
              />
              <h2 className="mt-4 text-2xl font-semibold tracking-tight sm:text-3xl">
                How can I help?
              </h2>
              <p className="mt-2 text-sm text-muted-foreground">
                Ask a question or upload a document.
              </p>
            </div>
          </div>
        ) : (
          <ChatContainerContent className="mx-auto w-full max-w-3xl gap-8 py-6">
            {messages.map((chatMessage) => (
              <ChatMessage key={chatMessage.id} message={chatMessage} />
            ))}
            <ChatContainerScrollAnchor />
          </ChatContainerContent>
        )}
      </ChatContainerRoot>

      <div className="shrink-0 px-3 pb-2 sm:px-6">
        <form className="mx-auto max-w-3xl" onSubmit={handleSubmit}>
          <InputGroup className="rounded-3xl bg-card shadow-xs">
            <label className="sr-only" htmlFor="chat-message">
              Message the assistant
            </label>
            <InputGroupTextarea
              className="min-h-16 px-3"
              disabled={isStreaming}
              id="chat-message"
              onChange={(event) => setMessage(event.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about your documents..."
              rows={2}
              value={message}
            />
            <InputGroupAddon align="block-end" className="justify-between">
              <InputGroupButton
                aria-label="Attach a document"
                disabled
                size="icon-sm"
                variant="ghost"
              >
                <Paperclip aria-hidden="true" />
              </InputGroupButton>
              <InputGroupButton
                aria-label="Send message"
                disabled={!message.trim() || isStreaming}
                size="icon-sm"
                type="submit"
              >
                <ArrowUp aria-hidden="true" />
              </InputGroupButton>
            </InputGroupAddon>
          </InputGroup>
        </form>
        <p className="mt-2 text-center text-xs text-muted-foreground">
          AI can make mistakes. Check important information.
        </p>
      </div>
    </section>
  )
}
