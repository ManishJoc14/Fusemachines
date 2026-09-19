"use client"

import { useState } from "react"
import { Check, ChevronDown, Copy, FileText, ListChecks } from "lucide-react"

import { Button } from "@/components/ui/button"
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"
import { Loader } from "@/components/ui/loader"
import { Markdown } from "@/components/ui/markdown"
import {
  Message,
  MessageAction,
  MessageActions,
  MessageContent,
} from "@/components/ui/message"
import { PromptSuggestion } from "@/components/ui/prompt-suggestion"
import {
  Steps,
  StepsContent,
  StepsItem,
  StepsTrigger,
} from "@/components/ui/steps"
import { Tool } from "@/components/ui/tool"
import type {
  AgentStats,
  AgentStepStats,
  AssistantMessage,
  ChatMessage as ChatMessageType,
  MessageAttachment,
  SourceReference,
  TokenUsageStats,
  ToolExecution,
} from "@/features/chat/types"

interface ChatMessageProps {
  message: ChatMessageType
  suggestionsDisabled?: boolean
  onSuggestionSelect: (suggestion: string) => void
}

export function ChatMessage({
  message,
  suggestionsDisabled = false,
  onSuggestionSelect,
}: ChatMessageProps) {
  if (message.role === "user") {
    return (
      <Message className="justify-end">
        <div className="flex max-w-[85%] flex-col items-end">
          <div className="max-w-full rounded-3xl bg-muted px-3 py-2.5 text-sm break-words text-foreground">
            {message.attachments?.length ? (
              <div className="mb-2 flex flex-wrap gap-2">
                {message.attachments.map((attachment) => (
                  <MessageAttachmentCard
                    attachment={attachment}
                    key={attachment.id}
                  />
                ))}
              </div>
            ) : null}
            <p className="px-1 whitespace-pre-wrap">{message.content}</p>
          </div>
          <MessageActions className="mt-1">
            <CopyMessageButton content={message.content} />
          </MessageActions>
        </div>
      </Message>
    )
  }

  return (
    <Message>
      <div className="min-w-0 flex-1">
        <AssistantActivity message={message} />

        {message.content ? (
          <MessageContent
            className="max-w-none bg-transparent p-0 text-sm leading-7"
            markdown
          >
            {message.content}
          </MessageContent>
        ) : null}

        {message.status === "error" ? (
          <p className="mt-2 text-sm text-destructive">Response interrupted</p>
        ) : null}

        {message.content ? (
          <MessageActions className="mt-1">
            <CopyMessageButton content={message.content} />
          </MessageActions>
        ) : null}

        {message.status === "complete" && message.followUpQuestions?.length ? (
          <div
            aria-label="Suggested next prompts"
            className="mt-3 flex flex-wrap gap-2"
          >
            {message.followUpQuestions.map((suggestion) => (
              <PromptSuggestion
                className="h-auto min-h-9 max-w-full justify-start py-2 text-left whitespace-normal"
                disabled={suggestionsDisabled}
                key={suggestion}
                onClick={() => onSuggestionSelect(suggestion)}
                size="sm"
              >
                {suggestion}
              </PromptSuggestion>
            ))}
          </div>
        ) : null}
      </div>
    </Message>
  )
}

function MessageAttachmentCard({
  attachment,
}: {
  attachment: MessageAttachment
}) {
  return (
    <div className="flex max-w-64 min-w-0 items-center gap-2 rounded-xl border bg-background/70 px-2.5 py-2">
      <span className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-muted">
        <FileText aria-hidden="true" className="size-4" />
      </span>
      <span className="min-w-0 text-left">
        <span className="block truncate font-medium">{attachment.name}</span>
        {attachment.chunkCount ? (
          <span className="block text-xs text-muted-foreground">
            {attachment.chunkCount} passages indexed
          </span>
        ) : null}
      </span>
    </div>
  )
}

function CopyMessageButton({ content }: { content: string }) {
  const [copied, setCopied] = useState(false)

  async function copyMessage() {
    await navigator.clipboard.writeText(content)
    setCopied(true)
    window.setTimeout(() => setCopied(false), 2000)
  }

  const label = copied ? "Copied" : "Copy message"

  return (
    <MessageAction tooltip={label}>
      <Button
        aria-label={label}
        className="size-8 cursor-pointer"
        onClick={copyMessage}
        size="icon"
        variant="ghost"
      >
        {copied ? (
          <Check aria-hidden="true" className="size-4" />
        ) : (
          <Copy aria-hidden="true" className="size-4" />
        )}
      </Button>
    </MessageAction>
  )
}

function AssistantActivity({ message }: { message: AssistantMessage }) {
  const activities = message.activities ?? []
  const hasDetails =
    activities.length > 0 ||
    message.tools.length > 0 ||
    message.sources.length > 0 ||
    Boolean(message.agent) ||
    Boolean(message.pipelineStats) ||
    Boolean(message.confidence) ||
    Boolean(message.model)

  if (!hasDetails) return null

  const isStreaming = message.status === "streaming"
  const summary = isStreaming
    ? (message.activity ?? "Working")
    : buildActivitySummary(message)

  return (
    <Steps className="mb-4" defaultOpen={isStreaming} key={message.status}>
      <StepsTrigger
        leftIcon={
          isStreaming ? (
            <Loader size="sm" variant="pulse-dot" />
          ) : (
            <ListChecks aria-hidden="true" className="size-4" />
          )
        }
      >
        {summary}
      </StepsTrigger>
      <StepsContent>
        {activities.map((activity, index) => (
          <StepsItem key={`${message.id}-activity-${index}`}>
            {activity}
          </StepsItem>
        ))}

        {message.agent ? <AgentTrajectory agent={message.agent} /> : null}

        {message.tools.map((tool, index) => (
          <Tool
            className="mt-0"
            defaultOpen={!tool.success}
            key={`${message.id}-tool-${index}`}
            toolPart={toToolPart(tool)}
          />
        ))}

        {message.sources.map((source) => (
          <SourcePassage key={source.chunk_id} source={source} />
        ))}

        {message.pipelineStats &&
        message.pipelineStats.retrieval_strategy !== "disabled" ? (
          <StepsItem>
            Retrieval: {formatRetrievalStrategy(message.pipelineStats)}
          </StepsItem>
        ) : null}

        {message.confidence ? (
          <StepsItem>Confidence: {capitalize(message.confidence)}</StepsItem>
        ) : null}

        {message.model ? (
          <StepsItem>
            Model: {message.model}
            {message.usedFallback ? " (fallback)" : ""}
          </StepsItem>
        ) : null}

        {message.agent?.token_usage.total_tokens ? (
          <TokenUsage usage={message.agent.token_usage} />
        ) : null}
      </StepsContent>
    </Steps>
  )
}

function AgentTrajectory({ agent }: { agent: AgentStats }) {
  return agent.trajectory.map((step, index) => (
    <StepsItem
      className={step.success === false ? "text-destructive" : undefined}
      key={`${step.iteration}-${step.tool_name ?? step.action}-${index}`}
    >
      {formatAgentStep(step)}
    </StepsItem>
  ))
}

function TokenUsage({ usage }: { usage: TokenUsageStats }) {
  return (
    <div
      aria-label="Token usage"
      className="mt-3 rounded-xl border bg-muted/30 p-3"
      role="group"
    >
      <p className="mb-2 text-xs font-medium text-foreground">Token usage</p>
      <dl className="grid grid-cols-3 gap-3">
        <TokenMetric label="Input" value={usage.prompt_tokens} />
        <TokenMetric label="Output" value={usage.completion_tokens} />
        <TokenMetric label="Total" value={usage.total_tokens} />
      </dl>
    </div>
  )
}

function TokenMetric({ label, value }: { label: string; value: number }) {
  return (
    <div className="min-w-0">
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="mt-0.5 truncate text-sm font-medium text-foreground tabular-nums">
        {value.toLocaleString()}
      </dd>
    </div>
  )
}

function SourcePassage({ source }: { source: SourceReference }) {
  return (
    <Collapsible>
      <CollapsibleTrigger className="group flex w-full cursor-pointer items-start gap-2 text-left">
        <FileText aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
        <span className="min-w-0 flex-1 text-sm text-muted-foreground">
          [{source.citation_number ?? source.chunk_index + 1}]{" "}
          {source.document_name} · Passage {source.chunk_index + 1}
        </span>
        <ChevronDown
          aria-hidden="true"
          className="mt-0.5 size-4 shrink-0 text-muted-foreground transition-transform group-data-[state=open]:rotate-180"
        />
      </CollapsibleTrigger>
      <CollapsibleContent className="pt-2 pl-6">
        <Markdown className="prose max-w-none text-sm leading-6 text-foreground">
          {source.text}
        </Markdown>
      </CollapsibleContent>
    </Collapsible>
  )
}

function buildActivitySummary(message: AssistantMessage): string {
  if (message.agent) {
    const steps = `${message.agent.iterations} step${message.agent.iterations === 1 ? "" : "s"}`
    const tokens = message.agent.token_usage.total_tokens
    return tokens
      ? `Completed in ${steps} · ${formatCompactNumber(tokens)} tokens`
      : `Completed in ${steps}`
  }

  const details = []
  if (message.tools.length) {
    details.push(
      `${message.tools.length} tool${message.tools.length === 1 ? "" : "s"}`
    )
  }
  if (message.sources.length) {
    details.push(
      `${message.sources.length} source${message.sources.length === 1 ? "" : "s"}`
    )
  }

  return details.length ? `Used ${details.join(" and ")}` : "Activity"
}

function formatAgentStep(step: AgentStepStats): string {
  if (step.action === "answer") {
    return `Step ${step.iteration}: Composed the final answer`
  }

  const toolName = step.tool_name?.replaceAll("_", " ") ?? "tool"
  const outcome = step.success === false ? "failed" : "completed"
  return `Step ${step.iteration}: ${toolName} ${outcome}`
}

function formatCompactNumber(value: number): string {
  return new Intl.NumberFormat("en", {
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(value)
}

function formatRetrievalStrategy(
  stats: NonNullable<AssistantMessage["pipelineStats"]>
): string {
  const strategy =
    stats.retrieval_strategy === "hybrid_rerank"
      ? "Hybrid search and reranking"
      : "Dense similarity search"
  const chunks = `${stats.retrieved_chunks} passage${stats.retrieved_chunks === 1 ? "" : "s"}`
  return `${strategy} · ${chunks}`
}

function capitalize(value: string): string {
  return value.charAt(0).toUpperCase() + value.slice(1)
}

function toToolPart(tool: ToolExecution) {
  return {
    type: tool.name,
    state: tool.success
      ? ("output-available" as const)
      : ("output-error" as const),
    input: tool.arguments,
    output: tool.success ? parseToolOutput(tool.output) : undefined,
    errorText: tool.success ? undefined : tool.output,
  }
}

function parseToolOutput(output: string): Record<string, unknown> {
  try {
    const parsed: unknown = JSON.parse(output)
    return isRecord(parsed) ? parsed : { result: parsed }
  } catch {
    return { result: output }
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value)
}
