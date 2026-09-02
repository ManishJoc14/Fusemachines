export type DocumentStatus = "uploading" | "ready" | "error"

export interface IngestionResult {
  document_id: string
  document_name: string
  character_count: number
  chunk_count: number
}

export interface SessionDocument {
  id: string
  name: string
  status: DocumentStatus
  characterCount?: number
  chunkCount?: number
  uploadedAt: string
  error?: string
}
