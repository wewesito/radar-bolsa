// Mini intérprete de Markdown para el contenido educativo (sin HTML: todo se pinta como texto).

export type Inline = { t: "text" | "bold" | "italic"; s: string } | { t: "link"; s: string; href: string };

export type Block =
  | { t: "h"; inline: Inline[] }
  | { t: "p"; inline: Inline[] }
  | { t: "quote"; inline: Inline[] }
  | { t: "ul" | "ol"; items: Inline[][] }
  | { t: "table"; head: Inline[][]; rows: Inline[][][] };

const INLINE = /\*\*(.+?)\*\*|\[([^\]]+)\]\((https:\/\/[^)\s]+)\)|\*([^*]+)\*/g;

export function parseInline(text: string): Inline[] {
  const out: Inline[] = [];
  let last = 0;
  for (const m of text.matchAll(INLINE)) {
    if (m.index > last) out.push({ t: "text", s: text.slice(last, m.index) });
    if (m[1] !== undefined) out.push({ t: "bold", s: m[1] });
    else if (m[2] !== undefined) out.push({ t: "link", s: m[2], href: m[3] });
    else out.push({ t: "italic", s: m[4] });
    last = m.index + m[0].length;
  }
  if (last < text.length) out.push({ t: "text", s: text.slice(last) });
  return out;
}

const cells = (line: string) => line.trim().replace(/^\||\|$/g, "").split("|").map((c) => parseInline(c.trim()));

export function parseMarkdown(src: string): Block[] {
  const lines = src.replace(/\r/g, "").split("\n");
  const blocks: Block[] = [];
  let para: string[] = [];
  const flush = () => {
    if (para.length) blocks.push({ t: "p", inline: parseInline(para.join(" ")) });
    para = [];
  };
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const trimmed = line.trim();
    if (!trimmed) {
      flush();
    } else if (/^#{1,6}\s/.test(trimmed)) {
      flush();
      blocks.push({ t: "h", inline: parseInline(trimmed.replace(/^#+\s*/, "")) });
    } else if (trimmed.startsWith(">")) {
      flush();
      const q = [trimmed.replace(/^>\s?/, "")];
      while (i + 1 < lines.length && lines[i + 1].trim().startsWith(">")) q.push(lines[++i].trim().replace(/^>\s?/, ""));
      blocks.push({ t: "quote", inline: parseInline(q.join(" ")) });
    } else if (trimmed.startsWith("|") && /^\|?[\s:|-]+\|?$/.test(lines[i + 1]?.trim() ?? "")) {
      flush();
      const head = cells(trimmed);
      i += 1;
      const rows: Inline[][][] = [];
      while (i + 1 < lines.length && lines[i + 1].trim().startsWith("|")) rows.push(cells(lines[++i]));
      blocks.push({ t: "table", head, rows });
    } else if (/^([-*]|\d+\.)\s/.test(trimmed)) {
      flush();
      const ordered = /^\d+\./.test(trimmed);
      const items: string[] = [];
      let cur = trimmed.replace(/^([-*]|\d+\.)\s+/, "");
      while (i + 1 < lines.length) {
        const next = lines[i + 1];
        const nt = next.trim();
        if (/^([-*]|\d+\.)\s/.test(nt)) {
          items.push(cur);
          cur = nt.replace(/^([-*]|\d+\.)\s+/, "");
          i++;
        } else if (nt && /^\s+\S/.test(next)) {
          cur += " " + nt; // continuación con sangría
          i++;
        } else break;
      }
      items.push(cur);
      blocks.push({ t: ordered ? "ol" : "ul", items: items.map(parseInline) });
    } else {
      para.push(trimmed);
    }
  }
  flush();
  return blocks;
}
