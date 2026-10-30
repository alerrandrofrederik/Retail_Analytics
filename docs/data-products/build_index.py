"""Gera docs/data-products/index.html, a página de produtos de dados, a partir dos produtos desta pasta.

Cada produto é uma subpasta com um README.md (uma seção "## " por aba) e um contrato *.odcs.yaml (a aba
Contrato). A página não busca nada na rede; as fontes vêm de reports/quality/fonts.

Uso, na raiz do repositório:
    uv run --no-project --with markdown --with pyyaml python docs/data-products/build_index.py
"""

import html
from pathlib import Path

import markdown
import yaml

HERE = Path(__file__).resolve().parent
TABS = ["Visão geral", "Guia", "Modelo de dados", "Métricas", "Consultas iniciais", "Qualidade", "Versões",
        "Pontos em aberto para o engenheiro de dados"]
STYLE = """
@font-face{font-family:'Bricolage Grotesque';font-weight:200 800;font-display:block;src:url('../../reports/quality/fonts/BricolageGrotesque-700.woff2') format('woff2');}
@font-face{font-family:'JetBrains Mono';font-weight:100 800;font-display:block;src:url('../../reports/quality/fonts/JetBrainsMono-500.woff2') format('woff2');}
*{margin:0;padding:0;box-sizing:border-box;}
:root{--bg:#080513;--plate:#1b1436;--ink:#ece7f8;--ink-2:rgba(236,231,248,.72);--line:rgba(236,231,248,.14);--line-2:rgba(236,231,248,.08);
  --purple:#8a63f2;--purple-soft:#c9b8ff;--orange:#ffa657;--green:#7ee0a8;}
html,body{background:var(--bg);}
body{font-family:'Bricolage Grotesque',sans-serif;color:var(--ink);font-size:19px;line-height:1.55;-webkit-font-smoothing:antialiased;
  background:radial-gradient(1500px 900px at 50% 300px,#161033 0%,#0e0a1d 55%,#080513 100%) no-repeat;}
main{max-width:1320px;margin:0 auto;padding:48px 40px 120px;}
code,pre,.mono{font-family:'JetBrains Mono',monospace;font-variant-ligatures:none;}
a{color:var(--purple-soft);text-decoration:none;}
h1{font-size:44px;font-weight:800;letter-spacing:-.02em;line-height:1.1;}
.sub{margin-top:8px;color:var(--ink-2);font-size:21px;}
.view{display:none;} .view.on{display:block;}
.cards{margin-top:32px;display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:18px;}
.pcard{border:1px solid rgba(173,150,255,.26);border-radius:14px;padding:22px;background:linear-gradient(160deg,#1b1436 0%,#110c24 100%);cursor:pointer;}
.pcard:hover{border-color:var(--purple-soft);}
.pcard .nm{font-size:24px;font-weight:700;} .pcard .desc{margin-top:8px;color:var(--ink-2);font-size:17px;}
.pcard .tl{margin-top:12px;font-family:'JetBrains Mono',monospace;font-size:15px;color:var(--purple-soft);}
.pcard .foot{margin-top:14px;display:flex;justify-content:space-between;font-size:15px;color:var(--ink-2);}
.cert{font-family:'JetBrains Mono',monospace;font-size:14px;color:var(--green);border:1px solid rgba(126,224,168,.4);border-radius:6px;padding:2px 8px;margin-left:10px;vertical-align:4px;}
.crumbs{font-size:16px;color:var(--ink-2);margin-bottom:14px;} .crumbs a{cursor:pointer;}
.tabs{margin-top:26px;display:flex;flex-wrap:wrap;gap:8px;border-bottom:1px solid var(--line);padding-bottom:12px;}
.tab{cursor:pointer;border:1px solid var(--line);border-radius:10px;padding:8px 16px;font-size:16px;color:var(--ink-2);}
.tab.on{color:var(--ink);background:rgba(138,99,242,.22);border-color:rgba(138,99,242,.55);}
.pp{display:none;margin-top:24px;} .pp.on{display:block;}
.pp p,.pp li{max-width:1100px;margin-top:10px;} .pp ol,.pp ul{padding-left:26px;}
.pp table{width:100%;border-collapse:collapse;margin-top:14px;}
.pp th{text-align:left;font-size:15px;color:var(--ink-2);font-weight:600;padding:8px 18px 8px 0;border-bottom:1px solid var(--line);}
.pp td{padding:9px 18px 9px 0;border-bottom:1px solid var(--line-2);vertical-align:top;font-size:17px;}
.pp code{font-size:.9em;color:var(--purple-soft);}
pre{margin-top:14px;background:#0d0919;border:1px solid var(--line);border-radius:10px;padding:16px 18px;overflow-x:auto;font-size:14.5px;line-height:1.6;color:#d6e0f5;}
pre code{color:inherit;font-size:inherit;}
@media (max-width:900px){.cards{grid-template-columns:1fr;} main{padding:24px 16px 80px;}}
"""
SCRIPT = """
document.querySelectorAll('[data-go]').forEach(function (el) { el.addEventListener('click', function () {
  document.querySelectorAll('.view').forEach(function (v) { v.classList.remove('on'); });
  document.getElementById(el.dataset.go).classList.add('on'); window.scrollTo(0, 0); }); });
document.querySelectorAll('.tab').forEach(function (t) { t.addEventListener('click', function () {
  var view = t.closest('.view');
  view.querySelectorAll('.tab').forEach(function (x) { x.classList.toggle('on', x === t); });
  view.querySelectorAll('.pp').forEach(function (p) { p.classList.toggle('on', p.dataset.pp === t.dataset.pt); }); }); });
"""


def sections(readme):
    """The README split by its '## ' headings: {heading: html}."""
    parts, current, title = {}, [], None
    for line in readme.splitlines():
        if line.startswith("## "):
            if title:
                parts[title] = "\n".join(current)
            title, current = line[3:].strip(), []
        elif title:
            current.append(line)
    if title:
        parts[title] = "\n".join(current)
    return {k: markdown.markdown(v, extensions=["tables", "fenced_code"]) for k, v in parts.items()}


def product(folder):
    readme = (folder / "README.md").read_text(encoding="utf-8")
    contract_path = next(folder.glob("*.odcs.yaml"))
    contract_text = contract_path.read_text(encoding="utf-8")
    contract = yaml.safe_load(contract_text)
    return {"key": folder.name, "title": readme.splitlines()[0].lstrip("# ").strip(), "sections": sections(readme),
            "contract": contract, "contract_text": contract_text, "contract_file": contract_path.name}


def render(products):
    cards, views = [], []
    for p in products:
        c = p["contract"]
        tables = " · ".join(s["physicalName"] for s in c["schema"])
        cards.append(f'<div class="pcard" data-go="v-{p["key"]}"><div class="nm">{html.escape(c.get("dataProduct", c["name"]))}'
                     f'<span class="cert">{c["version"]} · {c["status"]}</span></div>'
                     f'<div class="desc">{html.escape(c["description"]["purpose"])}</div><div class="tl">{html.escape(tables)}</div>'
                     f'<div class="foot"><span>{html.escape(c["customProperties"][0]["value"])}</span>'
                     f'<span>pronta até {c["slaProperties"][1]["value"][:5]} UTC</span></div></div>')
        tabs = [t for t in TABS if t in p["sections"]] + ["Contrato"]
        tab_html = "".join(f'<div class="tab{" on" if i == 0 else ""}" data-pt="t{i}">{t.split(" para ")[0]}</div>' for i, t in enumerate(tabs))
        panels = "".join(f'<div class="pp{" on" if i == 0 else ""}" data-pp="t{i}">{p["sections"][t]}</div>' for i, t in enumerate(tabs[:-1]))
        panels += (f'<div class="pp" data-pp="t{len(tabs) - 1}"><p>Contrato com o consumidor, <code>{p["contract_file"]}</code> '
                   f'(ODCS {c["apiVersion"]}, validado contra o JSON Schema).</p><pre><code>{html.escape(p["contract_text"])}</code></pre></div>')
        views.append(f'<section class="view" id="v-{p["key"]}"><div class="crumbs"><a data-go="v-hub">Produtos de dados</a> / {html.escape(c["name"])}</div>'
                     f'<h1>{html.escape(c.get("dataProduct", c["name"]))}<span class="cert">{c["version"]} · {c["status"]}</span></h1>'
                     f'<div class="sub">{html.escape(c["description"]["purpose"])}</div><div class="tabs">{tab_html}</div>{panels}</section>')
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Produtos de dados · Retail Analytics</title>
<style>{STYLE}</style>
</head>
<body>
<main>
<section class="view on" id="v-hub">
  <h1>Produtos de dados</h1>
  <div class="sub">O que a plataforma serve da camada gold de <span class="mono">lh_retail_analytics</span>, cada produto com o guia, as métricas e o contrato.</div>
  <div class="cards">{"".join(cards)}</div>
</section>
{"".join(views)}
</main>
<script>{SCRIPT}</script>
</body>
</html>
"""


def main():
    products = [product(f) for f in sorted(HERE.iterdir()) if f.is_dir() and (f / "README.md").exists()]
    (HERE / "index.html").write_text(render(products), encoding="utf-8")
    print(f"index.html: {len(products)} produto(s)")


if __name__ == "__main__":
    main()
