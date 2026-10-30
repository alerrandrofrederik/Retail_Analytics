"""Gera metadata/rystore.yaml a partir dos CSVs e dos documentos da fonte RYStore.

Skill: skills/metadata/SKILL.md. Os nomes e os tipos vêm dos dados; as chaves vêm do perfil
(reports/profile/rystore_profile.html); as descrições vêm só de data_dictionary.csv e README.md
da fonte. Nada é inventado: descrição ausente ou que contradiz os dados fica vazia e é listada.

Uso, na raiz do repositório:
    .venv/Scripts/python metadata/scripts/extract_metadata.py
"""

import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIR = ROOT / "RYStore-Retail-Dataset"
OUTPUT = ROOT / "metadata" / "rystore.yaml"

DOCUMENTS = ("data_dictionary.csv", "README.md")

# Chaves primárias do perfil da fonte (reports/profile/rystore_profile.html, "Chaves primárias").
PRIMARY_KEYS = {
    "orders": ["order_id"],
    "order_items": ["order_item_id"],
    "customers": ["customer_id"],
    "inventory": ["store_id", "product_id"],
    "employees": ["employee_id"],
    "products": ["product_id"],
    "suppliers": ["supplier_id"],
    "stores": ["store_id"],
    "promotions": ["promotion_id"],
}

# Colunas que são códigos e ficam texto, mesmo quando parecem números.
FORCE_STRING = re.compile(r"(_id|postcode.*)$")

# O tipo que cada texto genérico do dicionário afirma, para achar contradições com os dados.
DICTIONARY_CLAIMS = {
    "Integer count or threshold.": {"integer"},
    "Currency value in GBP.": {"decimal", "integer"},
    "Date/time value in ISO-style format.": {"date", "timestamp"},
    "Unique or foreign key identifier depending on table context.": {"string"},
    "UK-style VAT rate or VAT amount depending on column.": {"decimal", "integer"},
    "Categorical or descriptive attribute.": {"string", "boolean"},
}

PATTERNS = [
    ("boolean", re.compile(r"^(True|False)$")),
    ("integer", re.compile(r"^-?\d+$")),
    ("decimal", re.compile(r"^-?\d+(\.\d+)?$")),
    ("date", re.compile(r"^\d{4}-\d{2}-\d{2}$")),
    ("timestamp", re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")),
]


def read_rows(path):
    with path.open(newline="", encoding="ascii") as f:
        reader = csv.reader(f)
        header = next(reader)
        return header, list(reader)


def infer_type(column, values):
    """O tipo pelos valores não vazios. Decimais com parte .0 em todas as linhas contam como inteiro."""
    if FORCE_STRING.search(column):
        return "string", False
    filled = [v for v in values if v != ""]
    if not filled:
        return "string", False
    for name, pattern in PATTERNS:
        if all(pattern.match(v) for v in filled):
            if name == "decimal" and all(v.partition(".")[2].strip("0") == "" for v in filled):
                return "integer", True
            return name, False
    return "string", False


def read_dictionary():
    header, rows = read_rows(SOURCE_DIR / "data_dictionary.csv")
    return {(r[0].removesuffix(".csv"), r[1]): r[2] for r in rows}


def read_readme():
    """Descrição de cada tabela e as relações sugeridas, do README.md da fonte."""
    text = (SOURCE_DIR / "README.md").read_text(encoding="utf-8")
    tables = dict(re.findall(r"^- (\w+)\.csv: (.+)$", text, re.MULTILINE))
    relations = {}
    for child, target, rest in re.findall(r"^- (\w+\.\w+) -> (\w+\.\w+)(.*)$", text, re.MULTILINE):
        relations[child] = (target, "nullable" in rest)
    return tables, relations


def yaml_text(value):
    if value == "" or re.search(r"[:#'\"\[\]{}]|^[-?!&*|>%@`]", value):
        return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return value


def main():
    dictionary = read_dictionary()
    table_docs, relations = read_readme()

    tables = []
    report = {"from_document": 0, "empty_missing": [], "empty_contradiction": [], "float_integers": []}
    used_dictionary = set()

    for path in sorted(SOURCE_DIR.glob("*.csv")):
        table = path.stem
        if table == "data_dictionary":
            continue
        header, rows = read_rows(path)
        columns = []
        for i, column in enumerate(header):
            col_type, float_integer = infer_type(column, [r[i] for r in rows])
            if float_integer:
                report["float_integers"].append(f"{table}.{column}")
            text = dictionary.get((table, column), "")
            if (table, column) in dictionary:
                used_dictionary.add((table, column))
            if not text:
                report["empty_missing"].append(f"{table}.{column}")
            elif col_type not in DICTIONARY_CLAIMS.get(text, {col_type}):
                report["empty_contradiction"].append(f"{table}.{column}: dicionário diz '{text}', dados são {col_type}")
                text = ""
            else:
                report["from_document"] += 1
            relation = relations.get(f"{table}.{column}")
            if relation:
                target, nullable = relation
                text = (text + " " if text else "") + f"References {target}" + (", nullable." if nullable else ".")
            columns.append({
                "name": column,
                "type": col_type,
                "key": column in PRIMARY_KEYS.get(table, []),
                "description": text,
            })
        tables.append({"name": table, "description": table_docs.get(table, ""), "rows": len(rows), "columns": columns})

    unused = sorted(f"{t}.{c}" for t, c in dictionary.keys() - used_dictionary)

    lines = [
        "# A metadata da fonte RYStore, no formato de skills/metadata/references/purchasing.yaml.",
        "# Gerada por metadata/scripts/extract_metadata.py; não editar à mão, rodar o script de novo.",
        "# Nomes e tipos: dos CSVs em RYStore-Retail-Dataset/, lidos como texto.",
        "# Chaves: do perfil da fonte (reports/profile/rystore_profile.html).",
        "# Descrições das tabelas: RYStore-Retail-Dataset/README.md. Descrições das colunas:",
        "# RYStore-Retail-Dataset/data_dictionary.csv (textos genéricos da fonte), mais as relações do README.md.",
        "# Descrição vazia: o documento não diz nada ou contradiz os dados.",
        "",
        "source: rystore",
        "tables:",
    ]
    for t in tables:
        lines += ["", f"  - name: {t['name']}", f"    description: {yaml_text(t['description'])}", "    columns:"]
        for c in t["columns"]:
            lines.append(f"      - name: {c['name']}")
            lines.append(f"        type: {c['type']}")
            if c["key"]:
                lines.append("        key: true")
            lines.append(f"        description: {yaml_text(c['description'])}")
    OUTPUT.write_text("\n".join(lines) + "\n", encoding="utf-8")

    total = sum(len(t["columns"]) for t in tables)
    generic = sum(1 for t in tables for c in t["columns"] if c["description"])
    print(f"Escrito: {OUTPUT.relative_to(ROOT)}")
    print(f"Tabelas: {len(tables)}; colunas: {total}; linhas: {sum(t['rows'] for t in tables)}")
    print(f"Chaves: {sum(1 for t in tables for c in t['columns'] if c['key'])} colunas")
    print(f"Descrição de tabela vazia: {[t['name'] for t in tables if not t['description']]}")
    print(f"Descrições do dicionário usadas: {report['from_document']} (todas genéricas)")
    print(f"Colunas com descrição (dicionário e/ou relação): {generic}")
    print(f"Vazias, sem linha no dicionário: {report['empty_missing']}")
    print("Vazias, dicionário contradiz os dados:")
    for item in report["empty_contradiction"]:
        print(f"  - {item}")
    print(f"Inteiros serializados como decimal (.0): {report['float_integers']}")
    print(f"Linhas do dicionário sem coluna nos dados: {unused}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
