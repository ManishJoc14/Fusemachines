"use client"

import { ChatSidebar } from "@/components/chat/chat-sidebar"
import { ChatWorkspace } from "@/components/chat/chat-workspace"
import { useChatSessions } from "@/features/chat/use-chat-sessions"
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar"

export default function Page() {
  const {
    sessions,
    activeSession,
    activeSessionId,
    createSession,
    selectSession,
    deleteSession,
    sendMessage,
  } = useChatSessions()

  return (
    <SidebarProvider className="h-svh min-h-0 overflow-hidden">
      <ChatSidebar
        activeSessionId={activeSessionId}
        onCreateSession={createSession}
        onDeleteSession={deleteSession}
        onSelectSession={selectSession}
        sessions={sessions}
      />
      <SidebarInset className="h-full min-h-0 overflow-hidden">
        <ChatWorkspace
          isStreaming={
            activeSession?.messages.some(
              (message) =>
                message.role === "assistant" && message.status === "streaming"
            ) ?? false
          }
          messages={activeSession?.messages ?? []}
          onSendMessage={sendMessage}
          sessionTitle={activeSession?.title}
        />
      </SidebarInset>
    </SidebarProvider>
  )
}
