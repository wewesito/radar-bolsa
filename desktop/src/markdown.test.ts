import { describe, expect, it } from "vitest";
import { parseInline, parseMarkdown } from "./markdown";

describe("markdown", () => {
  it("interpreta negrita y enlaces https, y deja el HTML como texto", () => {
    const r = parseInline("**hola** <b>x</b> [AEAT](https://sede.agenciatributaria.gob.es)");
    expect(r[0]).toEqual({ t: "bold", s: "hola" });
    expect(r[1]).toEqual({ t: "text", s: " <b>x</b> " });
    expect(r[2]).toMatchObject({ t: "link", href: "https://sede.agenciatributaria.gob.es" });
  });
  it("no convierte enlaces que no son https", () => {
    expect(parseInline("[x](javascript:alert(1))").every((i) => i.t !== "link")).toBe(true);
  });
  it("reconoce títulos, listas con continuación, tablas y citas", () => {
    const b = parseMarkdown("#### Título\n- uno\n  sigue\n- dos\n\n| A | B |\n|---|---|\n| 1 | 2 |\n\n> aviso");
    expect(b.map((x) => x.t)).toEqual(["h", "ul", "table", "quote"]);
    const ul = b[1] as { items: unknown[] };
    expect(ul.items).toHaveLength(2);
    expect((b[2] as { rows: unknown[] }).rows).toHaveLength(1);
  });
});
