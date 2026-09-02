export const API_BASE_URL = (
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1"
).replace(/\/$/, "")

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number
  ) {
    super(message)
    this.name = "ApiError"
  }
}

export async function throwApiError(response: Response): Promise<never> {
  const message = await response.text()
  throw new ApiError(message || "The API request failed", response.status)
}
