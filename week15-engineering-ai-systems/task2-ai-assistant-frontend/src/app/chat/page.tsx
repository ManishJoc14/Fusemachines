"use client"

import { useEffect } from "react"
import { useRouter } from "next/navigation"

import { ChatSidebar } from "@/components/chat/chat-sidebar"
import { ChatWorkspace } from "@/components/chat/chat-workspace"
import { Loader } from "@/components/ui/loader"
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar"
import { useAuth } from "@/features/auth/auth-provider"
import { useChatSessions } from "@/features/chat/use-chat-sessions"

export default function ChatPage() {
  const router = useRouter()
  const { status, user, logout } = useAuth()
  const chat = useChatSessions(status === "authenticated")

  useEffect(() => {
    if (status === "unauthenticated") router.replace("/login")
  }, [router, status])

  if (status !== "authenticated" || !user) {
    return (
      <main className="flex min-h-svh items-center justify-center">
        <Loader aria-label="Loading chats" variant="circular" />
      </main>
    )
  }

  return (
    <SidebarProvider className="h-svh min-h-0 overflow-hidden">
      <ChatSidebar
        activeSessionId={chat.activeSessionId}
        onCreateSession={chat.createSession}
        onDeleteSession={chat.deleteSession}
        onLogout={logout}
        onSelectSession={chat.selectSession}
        sessions={chat.sessions}
        user={user}
      />
      <SidebarInset className="h-full min-h-0 overflow-hidden">
        <ChatWorkspace
          error={chat.error}
          isLoading={chat.isLoading}
          isStreaming={chat.isStreaming}
          messages={chat.activeSession?.messages ?? []}
          onSendMessage={chat.sendMessage}
          onStopGeneration={chat.stopGeneration}
          sessionTitle={chat.activeSession?.title}
        />
      </SidebarInset>
    </SidebarProvider>
  )
}
