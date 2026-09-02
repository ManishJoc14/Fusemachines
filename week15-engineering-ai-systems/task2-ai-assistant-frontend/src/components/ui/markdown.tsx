import { cn } from "@/lib/utils"
import { marked } from "marked"
import { memo, useId, useMemo } from "react"
import ReactMarkdown, { Components } from "react-markdown"
import remarkBreaks from "remark-breaks"
import remarkGfm from "remark-gfm"
import { CodeBlock, CodeBlockCode } from "./code-block"
import { MermaidDiagram } from "./mermaid-diagram"

export type MarkdownProps = {
  children: string
  id?: string
  className?: string
  components?: Partial<Components>
}

function parseMarkdownIntoBlocks(markdown: string): string[] {
  const tokens = marked.lexer(markdown)
  return tokens.map((token) => token.raw)
}

function extractLanguage(className?: string): string {
  if (!className) return "plaintext"
  const match = className.match(/language-(\w+)/)
  return match ? match[1] : "plaintext"
}

const INITIAL_COMPONENTS: Partial<Components> = {
  h1: function HeadingOne({ children }) {
    return (
      <h1 className="mt-8 mb-3 text-2xl font-semibold tracking-tight first:mt-0">
        {children}
      </h1>
    )
  },
  h2: function HeadingTwo({ children }) {
    return (
      <h2 className="mt-7 mb-3 text-xl font-semibold tracking-tight first:mt-0">
        {children}
      </h2>
    )
  },
  h3: function HeadingThree({ children }) {
    return (
      <h3 className="mt-6 mb-2 text-base font-semibold first:mt-0">
        {children}
      </h3>
    )
  },
  p: function Paragraph({ children }) {
    return <p className="my-3 leading-7 first:mt-0 last:mb-0">{children}</p>
  },
  ul: function UnorderedList({ children }) {
    return <ul className="my-3 list-disc space-y-1.5 pl-6">{children}</ul>
  },
  ol: function OrderedList({ children }) {
    return <ol className="my-3 list-decimal space-y-1.5 pl-6">{children}</ol>
  },
  li: function ListItem({ children }) {
    return <li className="pl-1 leading-7">{children}</li>
  },
  blockquote: function Blockquote({ children }) {
    return (
      <blockquote className="my-4 border-l-2 pl-4 text-muted-foreground">
        {children}
      </blockquote>
    )
  },
  table: function Table({ children }) {
    return (
      <div className="my-5 max-w-full overflow-x-auto rounded-lg border">
        <table className="w-full min-w-max border-collapse text-left text-sm">
          {children}
        </table>
      </div>
    )
  },
  th: function TableHeading({ children }) {
    return (
      <th className="border-b bg-muted/60 px-3 py-2.5 font-semibold">
        {children}
      </th>
    )
  },
  td: function TableCell({ children }) {
    return <td className="border-b px-3 py-2.5 align-top">{children}</td>
  },
  hr: function HorizontalRule() {
    return <hr className="my-6" />
  },
  a: function Link({ children, href }) {
    return (
      <a
        className="font-medium underline underline-offset-4"
        href={href}
        rel="noreferrer"
        target="_blank"
      >
        {children}
      </a>
    )
  },
  code: function CodeComponent({ className, children, ...props }) {
    const isInline =
      !props.node?.position?.start.line ||
      props.node?.position?.start.line === props.node?.position?.end.line

    if (isInline) {
      return (
        <span
          className={cn(
            "rounded-sm bg-primary-foreground px-1 font-mono text-sm",
            className
          )}
          {...props}
        >
          {children}
        </span>
      )
    }

    const language = extractLanguage(className)

    if (language === "mermaid") {
      return <MermaidDiagram code={String(children).trim()} />
    }

    return (
      <CodeBlock className={className}>
        <CodeBlockCode code={children as string} language={language} />
      </CodeBlock>
    )
  },
  pre: function PreComponent({ children }) {
    return <>{children}</>
  },
}

const MemoizedMarkdownBlock = memo(
  function MarkdownBlock({
    content,
    components = INITIAL_COMPONENTS,
  }: {
    content: string
    components?: Partial<Components>
  }) {
    return (
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkBreaks]}
        components={components}
      >
        {content}
      </ReactMarkdown>
    )
  },
  function propsAreEqual(prevProps, nextProps) {
    return prevProps.content === nextProps.content
  }
)

MemoizedMarkdownBlock.displayName = "MemoizedMarkdownBlock"

function MarkdownComponent({
  children,
  id,
  className,
  components = INITIAL_COMPONENTS,
}: MarkdownProps) {
  const generatedId = useId()
  const blockId = id ?? generatedId
  const blocks = useMemo(() => parseMarkdownIntoBlocks(children), [children])

  return (
    <div className={className}>
      {blocks.map((block, index) => (
        <MemoizedMarkdownBlock
          key={`${blockId}-block-${index}`}
          content={block}
          components={components}
        />
      ))}
    </div>
  )
}

const Markdown = memo(MarkdownComponent)
Markdown.displayName = "Markdown"

export { Markdown }
