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
  } = useChatSessions()

  return (
    <SidebarProvider>
      <ChatSidebar
        activeSessionId={activeSessionId}
        onCreateSession={createSession}
        onDeleteSession={deleteSession}
        onSelectSession={selectSession}
        sessions={sessions}
      />
      <SidebarInset className="h-svh overflow-hidden">
        <ChatWorkspace sessionTitle={activeSession?.title} />
      </SidebarInset>
    </SidebarProvider>
  )
}
