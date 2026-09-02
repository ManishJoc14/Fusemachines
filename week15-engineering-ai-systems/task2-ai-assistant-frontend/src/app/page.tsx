import { ChatSidebar } from "@/components/chat/chat-sidebar"
import { ChatWorkspace } from "@/components/chat/chat-workspace"
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar"

export default function Page() {
  return (
    <SidebarProvider>
      <ChatSidebar />
      <SidebarInset className="h-svh overflow-hidden">
        <ChatWorkspace />
      </SidebarInset>
    </SidebarProvider>
  )
}
