import "client-only"

import { API_BASE_URL, throwApiError } from "@/lib/api"

import type { BatchIngestionResult } from "./types"

export async function uploadDocuments(
  files: File[],
  signal?: AbortSignal
): Promise<BatchIngestionResult> {
  const formData = new FormData()
  files.forEach((file) => formData.append("files", file))

  const response = await fetch(`${API_BASE_URL}/documents/batch`, {
    method: "POST",
    body: formData,
    signal,
  })

  if (!response.ok) {
    await throwApiError(response)
  }

  return (await response.json()) as BatchIngestionResult
}
