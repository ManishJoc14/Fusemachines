export type ChatRole = "user" | "assistant"
export type Confidence = "low" | "medium" | "high"
export type MessageStatus = "streaming" | "complete" | "error"

export interface ChatHistoryMessage {
  role: ChatRole
  content: string
}

export interface ChatRequest {
  message: string
  history: ChatHistoryMessage[]
  use_rag: boolean
}

export interface SourceReference {
  chunk_id: string
  document_name: string
  chunk_index: number
  score: number
  text_preview: string
}

export interface ToolExecution {
  name: string
  arguments: Record<string, unknown>
  output: string
  success: boolean
}

export interface PipelineStats {
  retrieval_strategy: "dense_cosine" | "disabled"
  retrieved_chunks: number
  cited_chunks: number
  tool_executions: number
}

export interface ChatResponse {
  answer: string
  confidence: Confidence
  follow_up_questions: string[]
  sources: SourceReference[]
  tools_used: ToolExecution[]
  model: string
  used_fallback: boolean
  pipeline_stats: PipelineStats
}

interface BaseMessage {
  id: string
  content: string
  createdAt: string
}

export interface UserMessage extends BaseMessage {
  role: "user"
}

export interface AssistantMessage extends BaseMessage {
  role: "assistant"
  status: MessageStatus
  confidence?: Confidence
  sources: SourceReference[]
  tools: ToolExecution[]
  model?: string
  usedFallback?: boolean
}

export type ChatMessage = UserMessage | AssistantMessage

export interface ChatSession {
  id: string
  title: string
  messages: ChatMessage[]
  documentIds: string[]
  useRag: boolean
  createdAt: string
  updatedAt: string
}
