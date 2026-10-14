import { Fragment } from "react";
import { openExternal } from "../external";
import { parseMarkdown, type Block, type Inline } from "../markdown";

function Inlines({ items }: { items: Inline[] }) {
  return (
    <>
      {items.map((it, i) => {
        if (it.t === "bold") return <strong key={i}>{it.s}</strong>;
        if (it.t === "italic") return <em key={i}>{it.s}</em>;
        if (it.t === "link")
          return (
            <a key={i} href={it.href} onClick={(e) => { e.preventDefault(); openExternal(it.href); }}>{it.s}</a>
          );
        return <Fragment key={i}>{it.s}</Fragment>;
      })}
    </>
  );
}

function BlockView({ b }: { b: Block }) {
  switch (b.t) {
    case "h": return <h3 style={{ marginTop: 6 }}><Inlines items={b.inline} /></h3>;
    case "p": return <p style={{ lineHeight: 1.6 }}><Inlines items={b.inline} /></p>;
    case "quote": return <p className="error-box small" style={{ lineHeight: 1.55 }}><Inlines items={b.inline} /></p>;
    case "ul":
    case "ol": {
      const L = b.t;
      return <L style={{ paddingLeft: 22, lineHeight: 1.6, display: "grid", gap: 6 }}>{b.items.map((it, i) => <li key={i}><Inlines items={it} /></li>)}</L>;
    }
    case "table":
      return (
        <div className="table-wrap">
          <table className="data">
            <thead><tr>{b.head.map((c, i) => <th key={i}><Inlines items={c} /></th>)}</tr></thead>
            <tbody>{b.rows.map((r, i) => <tr key={i}>{r.map((c, j) => <td key={j}><Inlines items={c} /></td>)}</tr>)}</tbody>
          </table>
        </div>
      );
  }
}

export function Markdown({ text }: { text: string }) {
  return <div className="stack" style={{ gap: 12 }}>{parseMarkdown(text).map((b, i) => <BlockView key={i} b={b} />)}</div>;
}
