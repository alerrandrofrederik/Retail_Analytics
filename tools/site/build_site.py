"""Gera o site de documentação do projeto (skill toolkit) em docs/site/, a partir do repositório.

Lê o esquema do contrato (rystore_schema), as regras da silver, o SQL da gold, o job do bundle, o código
(grafo de chamadas pela AST), a metadata e o contrato. O que vem do Databricks (rodadas, checagens,
contagens, amostras, atualização) fica num snapshot, docs/site/data/snapshot.json, que só é atualizado
com --refresh: aí o script lê (só lê) o Databricks com o CLI, perfil pessoal. Sem --refresh, nada vai
à rede. As páginas não buscam nada na rede.

Uso, na raiz do repositório (reconstrua depois de cada release):
    uv run --with pyyaml python tools/site/build_site.py              # usa o snapshot
    uv run --with pyyaml python tools/site/build_site.py --refresh    # atualiza o snapshot e gera
"""

import argparse
import ast
import html
import json
import re
import subprocess
import sys
import tempfile
import time
from collections import defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "site"
SNAPSHOT = OUT / "data" / "snapshot.json"
sys.path.insert(0, str(ROOT / "retail_analytics" / "src"))

from retail_analytics import gold, rystore_schema, silver  # noqa: E402

CATALOG, PROFILE, JOB_NAME = "lh_retail_analytics", "pessoal", "rystore_pipeline"
PAGES = [("index.html", "Visão geral"), ("architecture.html", "Arquitetura"), ("lineage.html", "Linhagem"),
         ("calls.html", "Grafo de chamadas"), ("model.html", "Modelo de dados"), ("quality.html", "Qualidade"),
         ("runs.html", "Execuções"), ("catalog.html", "Catálogo")]
SAMPLE_ROWS = 3
e = html.escape


# ---------------------------------------------------------------- the repo

def repo_facts():
    """Everything the pages need that lives in the repository."""
    job = yaml.safe_load((ROOT / "retail_analytics/resources/rystore_pipeline.job.yml").read_text(encoding="utf-8"))
    job = job["resources"]["jobs"]["rystore_pipeline"]
    metadata = yaml.safe_load((ROOT / "metadata/rystore.yaml").read_text(encoding="utf-8"))
    contract = yaml.safe_load((ROOT / "contracts/rystore.odcs.yaml").read_text(encoding="utf-8"))
    descriptions = {(t["name"], c["name"]): c.get("description", "") for t in metadata["tables"] for c in t["columns"]}
    table_desc = {t["name"]: t.get("description", "") for t in metadata["tables"]}
    restricted = {(t["name"], p["name"]) for t in contract["schema"] for p in t["properties"] if p.get("classification") == "restricted"}
    gold_sources = {}
    for name, sql in gold.TABLES.items():
        found = re.findall(r"\b(?:FROM|JOIN)\s+([a-z_]+)", sql)
        gold_sources[name] = sorted({t for t in found if t in rystore_schema.COLUMNS})
    return {"job": job, "descriptions": descriptions, "table_desc": table_desc, "restricted": restricted,
            "gold_sources": gold_sources, "contract_version": rystore_schema.CONTRACT_VERSION}


def call_graph():
    """Functions of the pipeline code and the calls between them, from the AST (no import of the scripts).

    A call is resolved only when the code says where the function comes from: a function of the same module,
    a name imported from a module of the repo, module.function of an imported module, or self.method.
    Calls on other objects (s3.get_object, source.read) and builtins are left out, never guessed.
    Returns defs {id: (file, line)} and calls {(file, scope): {id}}, with id = "file:function" or "file:Class.method".
    """
    files = sorted((ROOT / "retail_analytics/src").rglob("*.py")) + sorted((ROOT / "scripts").glob("*.py"))
    by_module = {}  # importable module name -> file
    for f in files:
        rel = f.relative_to(ROOT).as_posix()
        by_module[f.stem] = rel
        if "retail_analytics/src/" in rel:
            by_module[rel.split("retail_analytics/src/")[1][:-3].replace("/", ".")] = rel
    defs, calls, trees = {}, defaultdict(set), {}
    for f in files:
        rel = f.relative_to(ROOT).as_posix()
        tree = ast.parse(f.read_text(encoding="utf-8"))
        trees[rel] = tree
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                defs[f"{rel}:{node.name}"] = (rel, node.lineno)
            elif isinstance(node, ast.ClassDef):
                for m in node.body:
                    if isinstance(m, ast.FunctionDef):
                        defs[f"{rel}:{node.name}.{m.name}"] = (rel, m.lineno)
    for rel, tree in trees.items():
        names, modules = {}, {}  # local name -> function id; local alias -> file
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                for a in node.names:
                    full = f"{node.module}.{a.name}"
                    if full in by_module:
                        modules[a.asname or a.name] = by_module[full]
                    elif node.module in by_module and f"{by_module[node.module]}:{a.name}" in defs:
                        names[a.asname or a.name] = f"{by_module[node.module]}:{a.name}"
            elif isinstance(node, ast.Import):
                for a in node.names:
                    if a.name in by_module:
                        modules[a.asname or a.name] = by_module[a.name]
        scopes = [("<módulo>", None, [n for n in tree.body if not isinstance(n, (ast.FunctionDef, ast.ClassDef))])]
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                scopes.append((node.name, None, node.body))
            elif isinstance(node, ast.ClassDef):
                scopes += [(f"{node.name}.{m.name}", node.name, m.body) for m in node.body if isinstance(m, ast.FunctionDef)]
        for scope, cls, body in scopes:
            for stmt in body:
                for sub in ast.walk(stmt):
                    if not isinstance(sub, ast.Call):
                        continue
                    target = None
                    if isinstance(sub.func, ast.Name):
                        target = names.get(sub.func.id) or (f"{rel}:{sub.func.id}" if f"{rel}:{sub.func.id}" in defs else None)
                    elif isinstance(sub.func, ast.Attribute) and isinstance(sub.func.value, ast.Name):
                        owner = sub.func.value.id
                        if owner in modules:
                            target = f"{modules[owner]}:{sub.func.attr}"
                        elif owner == "self" and cls:
                            target = f"{rel}:{cls}.{sub.func.attr}"
                    if target in defs and target != f"{rel}:{scope}":
                        calls[(rel, scope)].add(target)
    return defs, calls


# ---------------------------------------------------------------- the Databricks snapshot (read only)

def cli(*args):
    out = subprocess.run(["databricks", *args, "-p", PROFILE, "-o", "json"], capture_output=True, text=True, stdin=subprocess.DEVNULL)
    if out.returncode:
        raise RuntimeError(f"databricks {' '.join(args)}: {out.stderr.strip()[:300]}")
    return json.loads(out.stdout)


def refresh():
    """Read the runs, the checks, the counts, the samples and the freshness from Databricks into the snapshot."""
    import duckdb

    jobs = cli("jobs", "list")
    jobs = jobs if isinstance(jobs, list) else jobs.get("jobs", [])
    job_id = next(j["job_id"] for j in jobs if j["settings"]["name"].endswith(JOB_NAME))
    runs_list = cli("jobs", "list-runs", "--job-id", str(job_id))
    runs_list = runs_list if isinstance(runs_list, list) else runs_list.get("runs", [])
    runs = []
    for r in runs_list[:30]:
        d = cli("jobs", "get-run", str(r["run_id"]))
        runs.append({"run_id": str(d["run_id"]), "start": d["start_time"], "end": d.get("end_time"),
                     "result": d["state"].get("result_state") or d["state"].get("life_cycle_state"),
                     "message": d["state"].get("state_message", ""),
                     "tasks": [{"key": t["task_key"], "start": t.get("start_time"), "result": t["state"].get("result_state") or t["state"]["life_cycle_state"],
                                "setup": t.get("setup_duration", 0) // 1000, "exec": t.get("execution_duration", 0) // 1000}
                               for t in sorted(d.get("tasks", []), key=lambda t: t.get("start_time", 0))]})
    freshness = {}
    for t in gold.TABLES:
        freshness[f"gold.{t}"] = cli("tables", "get", f"{CATALOG}.gold.{t}")["updated_at"]
    with tempfile.TemporaryDirectory() as tmp:
        for layer in ("bronze", "silver", "gold"):
            subprocess.run(["databricks", "fs", "cp", "-r", f"dbfs:/Volumes/{CATALOG}/{layer}/files", f"{tmp}/{layer}", "-p", PROFILE],
                           capture_output=True, stdin=subprocess.DEVNULL, check=True)
        con = duckdb.connect()
        con.execute("SET TimeZone = 'UTC'")
        counts, samples = {}, {}
        for layer in ("bronze", "silver", "gold"):
            for folder in sorted(Path(tmp, layer).iterdir()):
                src = f"read_parquet('{folder.as_posix()}/*.parquet')"
                counts[f"{layer}.{folder.name}"] = con.execute(f"SELECT count(*) FROM {src}").fetchone()[0]
                if layer != "bronze" and not folder.name.startswith("_"):  # bronze keeps plain personal data: no sample
                    cur = con.execute(f"SELECT COLUMNS(*)::VARCHAR FROM {src} LIMIT {SAMPLE_ROWS}")
                    cols = [c[0] for c in cur.description]
                    # personal data never goes to the page, not even as its hash (an unsalted hash can be reversed)
                    hidden = set(silver.PERSONAL.get(folder.name, [])) if layer == "silver" else set()
                    rows = [["•••" if c in hidden and v is not None else v for c, v in zip(cols, row)] for row in cur.fetchall()]
                    samples[f"{layer}.{folder.name}"] = {"columns": cols, "rows": rows,
                                                         "types": [str(t) for t in con.execute(f"SELECT * FROM {src} LIMIT 0").description]}
        checks = con.execute(f"""SELECT strftime(run_at, '%Y-%m-%d %H:%M:%S'), table_name, check_name, status, failed_rows
                                 FROM read_parquet('{Path(tmp, 'silver', '_checks').as_posix()}/*.parquet') ORDER BY 1, 2, 3""").fetchall()
        types = {}
        for layer in ("silver", "gold"):
            for folder in sorted(Path(tmp, layer).iterdir()):
                desc = con.execute(f"DESCRIBE SELECT * FROM read_parquet('{folder.as_posix()}/*.parquet')").fetchall()
                types[f"{layer}.{folder.name}"] = [[c[0], c[1]] for c in desc]
    snapshot = {"taken_at": int(time.time() * 1000), "job_id": str(job_id), "runs": runs, "checks": [list(c) for c in checks],
                "counts": counts, "samples": samples, "types": types, "freshness": freshness}
    SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
    SNAPSHOT.write_text(json.dumps(snapshot, indent=1, ensure_ascii=False), encoding="utf-8")
    return snapshot


# ---------------------------------------------------------------- page helpers

def utc(ms):
    return time.strftime("%Y-%m-%d %H:%M", time.gmtime(ms / 1000)) if ms else "—"


def n(x):
    return f"{x:,}".replace(",", ".")


def page(filename, title, lead, body, script=""):
    style = (Path(__file__).parent / "style.css").read_text(encoding="utf-8")
    nav = "".join(f'<a class="p{" on" if f == filename else ""}" href="{f}">{label}</a>' for f, label in PAGES)
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)} · Retail Analytics</title>
<style>
{style}
.why2{{white-space:normal;color:var(--ink-2);}}
</style>
</head>
<body>
<nav><span class="brand">retail_analytics</span>{nav}<span class="built">gerado em {time.strftime('%Y-%m-%d %H:%M', time.gmtime())} UTC</span></nav>
<main>
  <h1>{e(title)}</h1>
  <p class="lead">{lead}</p>
{body}
</main>
<script>{script}</script>
</body>
</html>
"""


def kpis(items):
    return '<div class="kpis">' + "".join(f'<div class="kpi"><div class="l">{a}</div><div class="v">{b}</div><div class="sub">{c}</div></div>'
                                           for a, b, c in items) + "</div>"


def section(h2, one, inner):
    return f'<section class="s"><h2>{h2}</h2><p class="one">{one}</p>{inner}</section>'


def table(head, rows, cols=None):
    cg = "<colgroup>" + "".join(f'<col style="width:{c}">' for c in cols) + "</colgroup>" if cols else ""
    return (f'<div class="vis"><table class="t fixed">{cg}<tr>' + "".join(f"<th>{h}</th>" for h in head) + "</tr>"
            + "".join("<tr>" + "".join(f'<td class="{"m col" if i == 0 else "why2"}">{c}</td>' for i, c in enumerate(r)) + "</tr>" for r in rows)
            + "</table></div>")


LINEAGE_JS = """
document.querySelectorAll('.lin').forEach(function (root) {
  var nodes = Array.prototype.slice.call(root.querySelectorAll('.node')), wires = Array.prototype.slice.call(root.querySelectorAll('.wire'));
  var up = {}, down = {};
  wires.forEach(function (w) { (down[w.dataset.a] = down[w.dataset.a] || []).push(w.dataset.b); (up[w.dataset.b] = up[w.dataset.b] || []).push(w.dataset.a); });
  function walk(s, m) { var seen = {}, st = [s]; while (st.length) { (m[st.pop()] || []).forEach(function (x) { if (!seen[x]) { seen[x] = 1; st.push(x); } }); } return seen; }
  function clear() { nodes.concat(wires).forEach(function (x) { x.classList.remove('on', 'up', 'down', 'off'); }); }
  nodes.forEach(function (nd) { nd.addEventListener('click', function (ev) { ev.stopPropagation(); clear();
    var k = nd.dataset.k, u = walk(k, up), d = walk(k, down);
    nodes.forEach(function (o) { var ok = o.dataset.k; o.classList.add(ok === k ? 'on' : u[ok] ? 'up' : d[ok] ? 'down' : 'off'); });
    wires.forEach(function (w) { var a = w.dataset.a, b = w.dataset.b;
      w.classList.add((u[a] || a === k) && (u[b] || b === k) ? 'up' : (d[a] || a === k) && (d[b] || b === k) ? 'down' : 'off'); }); }); });
  document.addEventListener('click', clear); document.addEventListener('keydown', function (ev) { if (ev.key === 'Escape') clear(); });
  var h = decodeURIComponent(location.hash.slice(1)), hit = nodes.filter(function (x) { return x.dataset.k === h; })[0];
  if (hit) hit.dispatchEvent(new MouseEvent('click', {bubbles: true}));
});
"""


def graph(lanes, nodes, wires, node_w=230, lane_w=280, row_h=58, node_h=44):
    """An SVG of lanes of nodes (key, lane, title) with wires (a, b); the lineage script lights it on click."""
    rows = defaultdict(int)
    pos = {}
    for key, lane, _ in nodes:
        pos[key] = (lane * lane_w + 14, 54 + rows[lane] * row_h)
        rows[lane] += 1
    width, height = len(lanes) * lane_w, 54 + max(rows.values()) * row_h + 10
    out = [f'<svg viewBox="0 0 {width} {height}" width="{width}" height="{height}">']
    for i, name in enumerate(lanes):
        out.append(f'<rect class="lane" x="{i * lane_w + 2}" y="2" width="{lane_w - 10}" height="{height - 4}" rx="10"/>'
                   f'<text class="grp hd3" x="{i * lane_w + 14}" y="30">{e(name)}</text>')
    for a, b in wires:
        (x1, y1), (x2, y2) = pos[a], pos[b]
        mx = (x1 + node_w + x2) / 2
        out.append(f'<g class="wire" data-a="{a}" data-b="{b}"><path d="M{x1 + node_w},{y1 + node_h / 2} C{mx},{y1 + node_h / 2} '
                   f'{mx},{y2 + node_h / 2} {x2},{y2 + node_h / 2}"/></g>')
    for key, _, title in nodes:
        x, y = pos[key]
        out.append(f'<g class="node" data-k="{key}"><rect x="{x}" y="{y}" width="{node_w}" height="{node_h}"/>'
                   f'<text x="{x + 12}" y="{y + 28}">{e(title)}</text></g>')
    out.append("</svg>")
    return '<div class="vis wide paper"><div class="lin lin2">' + "".join(out) + "</div></div>"


# ---------------------------------------------------------------- the pages

def build(facts, snap, defs, calls):
    tables = list(rystore_schema.COLUMNS)
    counts = snap.get("counts", {})
    runs = snap.get("runs", [])
    last = runs[0] if runs else None
    checks = snap.get("checks", [])
    last_run_at = max((c[0] for c in checks), default=None)
    last_checks = [c for c in checks if c[0] == last_run_at]
    taken = utc(snap.get("taken_at"))
    pages = {}

    # index
    gold_rows = sum(v for k, v in counts.items() if k.startswith("gold."))
    layers = "".join(
        f'<div class="layer card"><div class="nm">{name}</div><div class="cnt">{n(cnt)}<small>{unit}</small></div><div class="sub">{sub}</div></div>'
        + ('<div class="arr"><svg viewBox="0 0 40 24"><path d="M4 12h30M26 5l8 7-8 7"/></svg></div>' if i < 3 else "")
        for i, (name, cnt, unit, sub) in enumerate([
            ("fonte RYStore", len(tables), "tabelas", "CSV no Supabase Storage, contrato " + facts["contract_version"]),
            ("bronze", sum(v for k, v in counts.items() if k.startswith("bronze.") and not k.split(".")[1].startswith("_")), "linhas", "texto, como chegou"),
            ("silver", sum(v for k, v in counts.items() if k.startswith("silver.") and not k.split(".")[1].startswith("_")), "linhas", "tipada, PII em hash, " + str(len(last_checks)) + " checagens"),
            ("gold", len(gold.TABLES), "tabelas", n(gold_rows) + " linhas, modelo estrela")]))
    last_html = "—"
    if last:
        last_html = table(["Tarefa", "Resultado", "Montagem", "Execução"],
                          [[t["key"], t["result"], f'{t["setup"]} s', f'{t["exec"]} s'] for t in last["tasks"]], ["300px", "200px", "160px", "auto"])
    page_list = "".join(f'<div class="prow"><a class="t1" href="{f}">{label}</a><span class="t2">{desc}</span><span class="t3">{f}</span></div>'
                        for (f, label), desc in zip(PAGES[1:], ["do que roda: o job, os volumes e o Unity Catalog", "cada tabela, clicável, antes e depois",
                                                                "quem chama o quê no código", "as entidades da fonte e o modelo estrela da gold",
                                                                "as checagens, rodada a rodada", "o que rodou, quanto tempo levou e o resultado",
                                                                "cada tabela e coluna, com uma amostra sem dados pessoais"]))
    body = kpis([("fontes", "1", "RYStore, 9 tabelas"), ("tabelas construídas", str(len(tables) * 2 + len(gold.TABLES)), "bronze, silver, gold"),
                 ("linhas na gold", n(gold_rows), f"{len(gold.TABLES)} tabelas"), ("checagens por rodada", str(len(last_checks)), "silver"),
                 ("rodadas", str(len(runs)), "no snapshot"), ("última rodada", last["result"] if last else "—", utc(last["start"]) if last else "")])
    body += section("As camadas", "Contagens do snapshot de " + taken + " UTC.", f'<div class="vis"><div class="layers cards">{layers}</div></div>')
    body += section("A última rodada", f'Rodada <span class="id">{last["run_id"] if last else "—"}</span>, iniciada em {utc(last["start"]) if last else "—"} UTC.', last_html)
    body += section("As páginas", "Geradas por tools/site/build_site.py a partir do repositório.", f'<div class="plist">{page_list}</div>')
    pages["index.html"] = page("index.html", "Visão geral", "A plataforma de dados da RYStore: uma fonte, três camadas e um job diário, tudo no catálogo lh_retail_analytics.", body)

    # architecture: from the job definition
    task_rows = []
    for t in facts["job"]["tasks"]:
        kind = next(k for k in t if k.endswith("_task"))
        dep = ", ".join(d["task_key"] for d in t.get("depends_on", [])) or "—"
        task_rows.append([f'<span class="id">{t["task_key"]}</span>', kind, f'<span class="id">{e(t[kind].get("python_file", ""))}</span>', dep])
    sched = facts["job"]["schedule"]
    deps = ", ".join(facts["job"]["environments"][0]["spec"]["dependencies"])
    arch_nodes = [("bucket", 0, "Supabase: bucket rystore")] + [(t["task_key"], 1, t["task_key"]) for t in facts["job"]["tasks"]] + \
        [("v_raw", 2, "volume bronze.raw"), ("v_bronze", 2, "volume bronze.files"), ("v_silver", 2, "volume silver.files"), ("v_gold", 2, "volume gold.files"),
         ("uc_bronze", 3, "schema bronze"), ("uc_silver", 3, "schema silver"), ("uc_gold", 3, "schema gold"), ("genie", 4, "consumo (Genie, SQL)")]
    arch_wires = [("bucket", "ingest_bronze"), ("ingest_bronze", "v_raw"), ("ingest_bronze", "v_bronze"), ("v_bronze", "build_silver"),
                  ("build_silver", "v_silver"), ("v_silver", "build_gold"), ("build_gold", "v_gold"), ("v_bronze", "publish"), ("v_silver", "publish"),
                  ("v_gold", "publish"), ("publish", "uc_bronze"), ("publish", "uc_silver"), ("publish", "uc_gold"), ("uc_gold", "genie")]
    arch_wires = [(a, b) for a, b in arch_wires if a in dict((k, 1) for k, *_ in arch_nodes) and b in dict((k, 1) for k, *_ in arch_nodes)]
    body = section("O desenho", f"Lido de resources/rystore_pipeline.job.yml: {len(facts['job']['tasks'])} tarefas serverless em Python puro (DuckDB e pyarrow, sem Spark). Clique numa caixa.",
                   graph(["origem", "tarefas do job", "volumes (Parquet)", "Unity Catalog", "consumo"], arch_nodes, arch_wires))
    body += section("As tarefas", f'Agendamento <span class="id">{e(sched["quartz_cron_expression"])}</span> ({sched["timezone_id"]}); ambiente com {e(deps)}.',
                    table(["Tarefa", "Tipo", "Arquivo", "Depende de"], task_rows, ["240px", "200px", "auto", "240px"]))
    pages["architecture.html"] = page("architecture.html", "Arquitetura", "Desenhada a partir do que roda: o job do bundle, os volumes e os schemas do catálogo.", body, LINEAGE_JS)

    # lineage
    lin_nodes = [(f"src_{t}", 0, f"{t}.csv") for t in tables] + [(f"bronze_{t}", 1, f"bronze.{t}") for t in tables] + \
                [(f"silver_{t}", 2, f"silver.{t}") for t in tables] + [(f"gold_{g}", 3, f"gold.{g}") for g in gold.TABLES]
    lin_wires = [(f"src_{t}", f"bronze_{t}") for t in tables] + [(f"bronze_{t}", f"silver_{t}") for t in tables] + \
                [(f"silver_{s}", f"gold_{g}") for g, srcs in facts["gold_sources"].items() for s in srcs]
    body = section("Cada tabela, antes e depois", "Clique numa tabela para acender o que a alimenta (roxo) e o que ela alimenta (laranja); Esc limpa. As ligações da gold vêm do SQL de gold.py (FROM e JOIN).",
                   graph(["fonte (bucket)", "bronze", "silver", "gold"], lin_nodes, lin_wires))
    body += section("A gold e as suas fontes", "Achadas no SQL, não de memória.",
                    table(["Tabela gold", "Lê da silver"], [[f'<span class="id">{g}</span>', ", ".join(srcs)] for g, srcs in facts["gold_sources"].items()], ["320px", "auto"]))
    pages["lineage.html"] = page("lineage.html", "Linhagem dos dados", "Da fonte à gold, tabela a tabela.", body, LINEAGE_JS)

    # calls
    called_by = defaultdict(set)
    for (module, scope), targets in calls.items():
        for target in targets:
            called_by[target].add(f"{module}:{scope}")

    def short(fid):  # "retail_analytics/src/retail_analytics/silver.py:build" -> "silver.build"
        file, func = fid.split(":")
        return f"{Path(file).stem}.{func}"

    def link(fid):
        return f'<a class="id" href="#{e(short(fid))}">{e(short(fid))}</a>'

    rows = []
    for fid, (file, line) in sorted(defs.items(), key=lambda kv: kv[1]):
        callees = sorted(calls.get((file, fid.split(":")[1]), set()))
        rows.append([f'<span class="id" id="{e(short(fid))}">{e(short(fid))}</span>', f'<span class="id">{e(file)}:{line}</span>',
                     ", ".join(link(c) for c in callees) or "—",
                     ", ".join(e(short(c)) for c in sorted(called_by.get(fid, set()))) or "—"])
    entry = [[f'<span class="id">{e(m)}</span>', ", ".join(link(c) for c in sorted(targets))]
             for (m, scope), targets in sorted(calls.items()) if scope == "<módulo>"]
    body = section("As entradas", "O código de cada script e de cada tarefa do job, fora de funções, e o que ele chama.", table(["Arquivo", "Chama"], entry, ["520px", "auto"]))
    body += section("As funções", f"{len(rows)} funções em retail_analytics/src e scripts/, lidas pela AST do Python; clique numa chamada para ir até ela.",
                    table(["Função", "Onde", "Chama", "É chamada por"], rows, ["220px", "380px", "auto", "auto"]))
    pages["calls.html"] = page("calls.html", "Grafo de chamadas", "Quem chama o quê no código do pipeline.", body)

    # model
    fk_rows = [[f'<span class="id">{t}.{c}</span>', f'<span class="id">{target}</span>'] for t, fks in rystore_schema.FOREIGN_KEYS.items() for c, target in fks]
    ent_rows = [[f'<span class="id">{t}</span>', ", ".join(rystore_schema.PRIMARY_KEYS[t]), rystore_schema.LOAD[t], e(facts["table_desc"].get(t, ""))] for t in tables]
    star = [[f'<span class="id">gold.{g}</span>', "fato" if g.startswith("fato") else "dimensão",
             ", ".join(c for c, _ in snap.get("types", {}).get(f"gold.{g}", []) if c.endswith("_id") or c.endswith("_key"))] for g in gold.TABLES]
    star_nodes = [(f"d_{g}", 0, g) for g in gold.TABLES if g.startswith("dim")] + [(f"f_{g}", 1, g) for g in gold.TABLES if g.startswith("fato")]
    # a dimension joins a fact when the fact has the key column of the dimension (its first column)
    types = snap.get("types", {})
    dim_key = {g: types[f"gold.{g}"][0][0] for g in gold.TABLES if g.startswith("dim") and f"gold.{g}" in types}
    star_wires = [(f"d_{d}", f"f_{f}") for f in gold.TABLES if f.startswith("fato") for d, k in dim_key.items()
                  if any(c == k or c.endswith("_" + k) for c, _ in types.get(f"gold.{f}", []))]
    body = section("As entidades da fonte", f"{len(tables)} tabelas do contrato {facts['contract_version']}, com a chave e a carga.",
                   table(["Tabela", "Chave", "Carga", "Descrição (metadata)"], ent_rows, ["220px", "260px", "120px", "auto"]))
    body += section("Os relacionamentos", f"{len(fk_rows)} chaves estrangeiras do contrato, conferidas na silver (órfãos vão para a quarentena).",
                    table(["Coluna", "Aponta para"], fk_rows, ["420px", "auto"]))
    body += section("O modelo estrela da gold", "Dimensões à esquerda, fatos à direita; uma ligação quando o fato tem a chave da dimensão (do snapshot). Clique numa caixa.",
                    graph(["dimensões", "fatos"], star_nodes, star_wires, lane_w=420, node_w=300))
    body += section("As chaves de cada tabela gold", "Colunas *_id e *_key, do snapshot.", table(["Tabela", "Tipo", "Chaves"], star, ["320px", "160px", "auto"]))
    pages["model.html"] = page("model.html", "Modelo de dados", "As entidades da fonte e o modelo estrela da gold.", body, LINEAGE_JS)

    # quality
    run_ats = sorted({c[0] for c in checks})
    by_check = defaultdict(dict)
    for run_at, t, name, status, failed in checks:
        by_check[(t, name)][run_at] = (status, failed)
    strips = []
    for (t, name), results in sorted(by_check.items()):
        cells = "".join(f'<i class="{ {"pass": "", "warn": "orange", "fail": "red"}[results[r][0]] if r in results else "dim"}" title="{r}"></i>' for r in run_ats)
        bad = sum(1 for s, _ in results.values() if s != "pass")
        strips.append(f'<div class="strip"><span class="nm"><span class="id">{e(name)}</span> <span class="dim">· {t}</span></span>'
                      f'<span class="cells">{cells}</span><span class="cnt"><b>{len(results) - bad}</b> de {len(results)} pass</span></div>')
    rule_rows = [[f'<span class="id">{name}</span>', t, level, f'<span class="id">{e(sql)}</span>'] for t, name, level, sql in silver.RULES]
    body = kpis([("checagens na última rodada", str(len(last_checks)), last_run_at or "—"),
                 ("falharam", str(sum(1 for c in last_checks if c[3] == "fail")), "última rodada"),
                 ("alertaram", str(sum(1 for c in last_checks if c[3] == "warn")), "última rodada"),
                 ("em quarentena", n(counts.get("silver._quarantine", 0)), "silver"),
                 ("listas fechadas", str(len(rystore_schema.VALID_VALUES)), "do contrato"), ("rodadas com checagens", str(len(run_ats)), "no snapshot")])
    body += section("Todas as checagens, rodada a rodada", "Roxo é pass, laranja warn, vermelho fail, cinza quando a checagem ainda não existia.",
                    f'<div class="vis wide paper"><div class="strips">{"".join(strips)}</div></div>')
    body += section("As regras de negócio", "Lidas de silver.RULES; cada uma conta as linhas que quebram a regra.", table(["Checagem", "Tabela", "Nível", "SQL"], rule_rows, ["260px", "160px", "100px", "auto"]))
    pages["quality.html"] = page("quality.html", "Qualidade dos dados", "As checagens da silver e os seus resultados, do snapshot de " + taken + " UTC.", body)

    # runs
    run_rows = []
    for r in runs:
        dur = f'{(r["end"] - r["start"]) // 60000} min' if r.get("end") else "—"
        tasks = ", ".join(f'{t["key"]} {t["result"]} ({t["setup"]}+{t["exec"]} s)' for t in r["tasks"])
        run_rows.append([r["run_id"], utc(r["start"]), dur, r["result"], e(tasks)])
    fresh = [[f'<span class="id">{k}</span>', utc(v)] for k, v in sorted(snap.get("freshness", {}).items())]
    body = section("As rodadas do job", f'Job <span class="id">{JOB_NAME}</span>; tempos de montagem + execução por tarefa.',
                   table(["Rodada", "Início (UTC)", "Duração", "Resultado", "Tarefas"], run_rows, ["220px", "190px", "120px", "160px", "auto"]))
    body += section("A atualização da gold", "Quando cada tabela foi reconstruída pela última vez; o SLA é 08:00 UTC.", table(["Tabela", "Atualizada (UTC)"], fresh, ["420px", "auto"]))
    pages["runs.html"] = page("runs.html", "Execuções", "O que rodou, quanto tempo levou e o resultado.", body)

    # catalog
    blocks = []
    for key in sorted(snap.get("types", {})):
        layer, t = key.split(".")
        cols = snap["types"][key]
        sample = snap.get("samples", {}).get(key, {"columns": [], "rows": []})
        col_rows = []
        for name, typ in cols:
            idx = sample["columns"].index(name) if name in sample["columns"] else None
            values = ", ".join(sorted({(r[idx] or "∅")[:18] + ("…" if r[idx] and len(r[idx]) > 18 else "") for r in sample["rows"]})) if idx is not None else ""
            source_table = t if t in rystore_schema.COLUMNS else None
            pii = "PII em SHA-256" if source_table and (source_table, name) in facts["restricted"] else ""
            desc = facts["descriptions"].get((source_table, name), "") if source_table else ""
            col_rows.append(f'<div class="col"><span class="cn">{e(name)}</span><span class="ct">{e(typ)}</span><span class="cd">{e(pii or desc)}</span></div>'
                            f'<div class="col"><span class="cn"></span><span class="ct"></span><span class="cd dim">{e(values)}</span></div>')
        blocks.append(f'<div class="crow" data-s="{key} {" ".join(c for c, _ in cols)}"><div class="chead"><span class="tri">▸</span><span class="nm">{key}</span>'
                      f'<span class="tags"><span class="tag">{layer}</span></span><span class="meta"><span>{n(counts.get(key, 0))} linhas</span><span>{len(cols)} colunas</span><span></span><span></span></span>'
                      f'<span class="ds">{e(facts["table_desc"].get(t, ""))}</span></div><div class="cols">{"".join(col_rows)}</div></div>')
    cat_js = """
document.querySelectorAll('.crow .chead').forEach(function (h) { h.addEventListener('click', function () { h.parentNode.classList.toggle('open'); }); });
var q = document.getElementById('q');
q.addEventListener('input', function () { var v = q.value.toLowerCase(), shown = 0;
  document.querySelectorAll('.crow').forEach(function (r) { var ok = r.dataset.s.toLowerCase().indexOf(v) >= 0; r.classList.toggle('hidden', !ok); shown += ok; });
  document.getElementById('qn').textContent = shown + ' tabelas'; });
"""
    body = (f'<div class="search"><input id="q" type="search" placeholder="Buscar tabela ou coluna"><span class="n" id="qn">{len(blocks)} tabelas</span></div>'
            f'<div class="csec">{"".join(blocks)}</div>')
    pages["catalog.html"] = page("catalog.html", "Catálogo de dados", "Cada tabela da silver e da gold, com as colunas, os tipos e uma amostra. A bronze não tem amostra: guarda a PII aberta. Na silver, a PII já está em SHA-256.", body, cat_js)
    return pages


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--refresh", action="store_true", help="lê o Databricks (só leitura) e atualiza o snapshot antes de gerar")
    args = parser.parse_args()
    snap = refresh() if args.refresh else json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    defs, calls = call_graph()
    pages = build(repo_facts(), snap, defs, calls)
    for name, text in pages.items():
        (OUT / name).write_text(text, encoding="utf-8")
    print(f"{len(pages)} páginas em {OUT.relative_to(ROOT).as_posix()}/ (snapshot de {utc(snap['taken_at'])} UTC); abra docs/site/index.html")


if __name__ == "__main__":
    main()
