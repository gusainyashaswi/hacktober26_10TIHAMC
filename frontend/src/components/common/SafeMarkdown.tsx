import React from 'react';

interface SafeMarkdownProps {
  content: string;
  className?: string;
}

export function SafeMarkdown({ content, className = '' }: SafeMarkdownProps) {
  if (!content) return null;

  const elements = parseMarkdown(content);

  return <div className={`markdown-body ${className}`}>{elements}</div>;
}

function parseMarkdown(text: string): React.ReactNode[] {
  const lines = text.split(/\r?\n/);
  const nodes: React.ReactNode[] = [];
  let index = 0;

  let inCodeBlock = false;
  let codeBlockLines: string[] = [];

  let inList = false;
  let listItems: React.ReactNode[] = [];

  const flushList = () => {
    if (inList && listItems.length > 0) {
      nodes.push(
        <ul key={`ul-${index++}`} className="md-list">
          {listItems}
        </ul>,
      );
      listItems = [];
      inList = false;
    }
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    // Code block toggle
    if (line.trim().startsWith('```')) {
      if (inCodeBlock) {
        // Close code block
        nodes.push(
          <pre key={`code-${index++}`} className="md-pre">
            <code className="md-code-block">{codeBlockLines.join('\n')}</code>
          </pre>,
        );
        codeBlockLines = [];
        inCodeBlock = false;
      } else {
        flushList();
        inCodeBlock = true;
      }
      continue;
    }

    if (inCodeBlock) {
      codeBlockLines.push(line);
      continue;
    }

    // Empty line flushes lists and acts as paragraph separator
    if (!line.trim()) {
      flushList();
      continue;
    }

    // Headings
    if (line.startsWith('# ')) {
      flushList();
      nodes.push(
        <h1 key={`h1-${index++}`} className="md-h1">
          {parseInline(line.slice(2))}
        </h1>,
      );
      continue;
    }
    if (line.startsWith('## ')) {
      flushList();
      nodes.push(
        <h2 key={`h2-${index++}`} className="md-h2">
          {parseInline(line.slice(3))}
        </h2>,
      );
      continue;
    }
    if (line.startsWith('### ')) {
      flushList();
      nodes.push(
        <h3 key={`h3-${index++}`} className="md-h3">
          {parseInline(line.slice(4))}
        </h3>,
      );
      continue;
    }
    if (line.startsWith('#### ')) {
      flushList();
      nodes.push(
        <h4 key={`h4-${index++}`} className="md-h4">
          {parseInline(line.slice(5))}
        </h4>,
      );
      continue;
    }

    // Blockquote
    if (line.startsWith('> ')) {
      flushList();
      nodes.push(
        <blockquote key={`bq-${index++}`} className="md-blockquote">
          {parseInline(line.slice(2))}
        </blockquote>,
      );
      continue;
    }

    // Unordered List item
    const listMatch = line.match(/^(\s*)[-*+]\s+(.*)$/);
    if (listMatch) {
      inList = true;
      listItems.push(
        <li key={`li-${index++}`} className="md-li">
          {parseInline(listMatch[2])}
        </li>,
      );
      continue;
    }

    // Ordered List item
    const numListMatch = line.match(/^(\s*)\d+\.\s+(.*)$/);
    if (numListMatch) {
      inList = true;
      listItems.push(
        <li key={`li-${index++}`} className="md-li">
          {parseInline(numListMatch[2])}
        </li>,
      );
      continue;
    }

    flushList();

    // Standard paragraph
    nodes.push(
      <p key={`p-${index++}`} className="md-p">
        {parseInline(line)}
      </p>,
    );
  }

  flushList();

  // If code block was not closed
  if (inCodeBlock && codeBlockLines.length > 0) {
    nodes.push(
      <pre key={`code-${index++}`} className="md-pre">
        <code className="md-code-block">{codeBlockLines.join('\n')}</code>
      </pre>,
    );
  }

  return nodes;
}

function parseInline(text: string): React.ReactNode[] {
  const parts: React.ReactNode[] = [];
  let remaining = text;
  let key = 0;

  while (remaining.length > 0) {
    // Inline code `...`
    const codeMatch = remaining.match(/^(.*?)`([^`]+)`(.*)$/);
    // Bold **...**
    const boldMatch = remaining.match(/^(.*?)\*\*([^*]+)\*\*(.*)$/);
    // Link [text](url)
    const linkMatch = remaining.match(/^(.*?)\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)(.*)$/);

    // Find the earliest match
    let earliestType: 'code' | 'bold' | 'link' | null = null;
    let earliestIndex = Infinity;

    if (codeMatch && codeMatch[1].length < earliestIndex) {
      earliestIndex = codeMatch[1].length;
      earliestType = 'code';
    }
    if (boldMatch && boldMatch[1].length < earliestIndex) {
      earliestIndex = boldMatch[1].length;
      earliestType = 'bold';
    }
    if (linkMatch && linkMatch[1].length < earliestIndex) {
      earliestIndex = linkMatch[1].length;
      earliestType = 'link';
    }

    if (!earliestType) {
      parts.push(remaining);
      break;
    }

    if (earliestType === 'code' && codeMatch) {
      if (codeMatch[1]) parts.push(codeMatch[1]);
      parts.push(
        <code key={`c-${key++}`} className="md-inline-code">
          {codeMatch[2]}
        </code>,
      );
      remaining = codeMatch[3];
    } else if (earliestType === 'bold' && boldMatch) {
      if (boldMatch[1]) parts.push(boldMatch[1]);
      parts.push(
        <strong key={`b-${key++}`} className="md-bold">
          {boldMatch[2]}
        </strong>,
      );
      remaining = boldMatch[3];
    } else if (earliestType === 'link' && linkMatch) {
      if (linkMatch[1]) parts.push(linkMatch[1]);
      parts.push(
        <a
          key={`a-${key++}`}
          href={linkMatch[3]}
          target="_blank"
          rel="noopener noreferrer"
          className="md-link"
        >
          {linkMatch[2]}
        </a>,
      );
      remaining = linkMatch[4];
    }
  }

  return parts;
}
