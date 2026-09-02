"use client"

import { useState, type FormEvent, type KeyboardEvent } from "react"
import Image from "next/image"
import { ArrowUp, Paperclip } from "lucide-react"

import assistantLogo from "@/app/icon1.png"
import {
  InputGroup,
  InputGroupAddon,
  InputGroupButton,
  InputGroupTextarea,
} from "@/components/ui/input-group"
import { Separator } from "@/components/ui/separator"
import { SidebarTrigger } from "@/components/ui/sidebar"
import type { ChatMessage } from "@/features/chat/types"

interface ChatWorkspaceProps {
  messages: ChatMessage[]
  sessionTitle?: string
  onSendMessage: (message: string) => void
}

export function ChatWorkspace({
  messages,
  sessionTitle,
  onSendMessage,
}: ChatWorkspaceProps) {
  const [message, setMessage] = useState("")

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!message.trim()) return

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
    <section className="flex min-w-0 flex-1 flex-col">
      <header className="flex h-14 shrink-0 items-center px-3 sm:px-4">
        <div className="flex min-w-0 items-center gap-2">
          <SidebarTrigger aria-label="Open chat sessions" />
          <Separator className="mt-2 mr-1 h-4" orientation="vertical" />
          <h1 className="truncate text-sm font-semibold">
            {sessionTitle ?? "AI Assistant"}
          </h1>
        </div>
      </header>

      <div className="min-h-0 flex-1 overflow-y-auto px-4">
        {messages.length === 0 ? (
          <div className="flex h-full flex-col">
            <div className="m-auto w-full max-w-3xl pb-20 text-center">
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
          <div className="mx-auto flex w-full max-w-3xl flex-col gap-6 py-6">
            {messages.map((chatMessage) => (
              <div
                className={
                  chatMessage.role === "user"
                    ? "ml-auto max-w-[85%] rounded-3xl bg-muted px-4 py-2.5 text-sm whitespace-pre-wrap"
                    : "max-w-none text-sm whitespace-pre-wrap"
                }
                key={chatMessage.id}
              >
                {chatMessage.content}
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="shrink-0 px-3 pb-2 sm:px-6">
        <form className="mx-auto max-w-3xl" onSubmit={handleSubmit}>
          <InputGroup className="rounded-3xl bg-card shadow-xs">
            <label className="sr-only" htmlFor="chat-message">
              Message the assistant
            </label>
            <InputGroupTextarea
              className="min-h-16 px-3"
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
                disabled={!message.trim()}
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
