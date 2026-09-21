import json
from pathlib import Path

base = Path(r"c:\Users\andre\OneDrive\Desktop\Universidad\Desarrollo de software\primer-parcial\notebooks")
out_dir = Path(r"c:\Users\andre\OneDrive\Desktop\Universidad\Desarrollo de software\primer-parcial\_extract_tmp")
out_dir.mkdir(exist_ok=True)

nbs = [
    "02_exploracion_caracterizacion_datos.ipynb",
    "03_limpieza_datos.ipynb",
    "04_pipeline_etl_mysql.ipynb",
    "05_consultas_analisis_cientifico.ipynb",
]

for name in nbs:
    p = base / name
    print(f"=== {name} exists={p.exists()} size={p.stat().st_size if p.exists() else 0}")
    nb = json.loads(p.read_text(encoding="utf-8"))
    md_parts = []
    out_parts = []
    for i, cell in enumerate(nb.get("cells", [])):
        ctype = cell.get("cell_type")
        src = "".join(cell.get("source", []))
        if ctype == "markdown":
            md_parts.append(f"===== CELL {i} MARKDOWN =====\n{src}\n")
        elif ctype == "code":
            outs = []
            for o in cell.get("outputs", []):
                ot = o.get("output_type")
                if ot == "stream":
                    outs.append("".join(o.get("text", [])))
                elif ot in ("execute_result", "display_data"):
                    data = o.get("data", {})
                    if "text/plain" in data:
                        tp = data["text/plain"]
                        outs.append("".join(tp) if isinstance(tp, list) else tp)
                elif ot == "error":
                    outs.append("ERROR: " + "\n".join(o.get("traceback", [])[-3:]))
            if outs:
                joined = "\n".join(outs)
                if "pandas.pydata.org" in joined and len(joined) < 800:
                    continue
                if len(joined) > 12000:
                    joined = joined[:12000] + "\n...[TRUNCATED]..."
                out_parts.append(
                    f"===== CELL {i} CODE SRC (first 500) =====\n{src[:500]}\n----- OUTPUT -----\n{joined}\n"
                )
    (out_dir / f"{name}_md.txt").write_text("\n".join(md_parts), encoding="utf-8")
    (out_dir / f"{name}_out.txt").write_text("\n".join(out_parts), encoding="utf-8")
    ncells = len(nb.get("cells", []))
    print(f"  md_chars={sum(len(x) for x in md_parts)} out_chars={sum(len(x) for x in out_parts)} cells={ncells}")

print("DONE", out_dir)
