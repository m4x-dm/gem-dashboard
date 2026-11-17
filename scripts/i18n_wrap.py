"""Polautomatyczne opakowanie tekstow UI w tr() (narzedzie deweloperskie, i18n).

Uzycie:
    python scripts/i18n_wrap.py PLIK [PLIK...]          # zmienia pliki, wypisuje raport
    python scripts/i18n_wrap.py --dry PLIK [PLIK...]    # tylko raport

Co robi (na podstawie AST, bez zgadywania regexami):
- pierwszy argument-stala w wywolaniach UI Streamlita (st.markdown/caption/button/...,
  rowniez col.metric, tab.markdown itd. — liczy sie nazwa metody),
- elementy listy w st.tabs([...]),
- kwargi z trescia: help, placeholder, label, title, caption, xaxis_title, yaxis_title,
  title_text, name (tylko w go.* — nazwy serii na wykresie),
- pierwszy argument w znanych helperach (premium_teaser, _base_layout, unavailable, ...).
Pomija: teksty bez liter, HTML/CSS (zaczyna sie od "<"), juz opakowane, opcje selectboxow
(to wartosci logiki — tlumaczy sie je przez format_func=tr recznie).
Raportuje f-stringi w tych samych pozycjach — do recznego przerobienia na tr("..{x}..", x=...).
"""
from __future__ import annotations

import ast
import re
import sys

UI_METHODS = {
    "markdown", "caption", "subheader", "header", "title", "info", "warning", "error", "success",
    "toast", "button", "download_button", "link_button", "expander", "checkbox", "toggle", "radio",
    "selectbox", "multiselect", "slider", "select_slider", "number_input", "text_input",
    "text_area", "date_input", "metric", "spinner", "popover", "segmented_control", "status",
    "form_submit_button", "pills", "write", "exception",
}
HELPERS = {"premium_teaser", "_base_layout", "unavailable", "_finance_empty", "render_lock_screen",
           "status_card", "_metric_card", "final_value_card", "macro_card", "comparison_card"}
TEXT_KWARGS = {"help", "placeholder", "label", "title", "caption", "xaxis_title", "yaxis_title",
               "title_text", "yaxis2_title", "legend_title", "legend_title_text"}
LETTER = re.compile(r"[A-Za-zĄĆĘŁŃÓŚŹŻąćęłńóśźż]{2,}")


def _wants(node) -> bool:
    if not (isinstance(node, ast.Constant) and isinstance(node.value, str)):
        return False
    s = node.value.strip()
    return bool(s) and not s.startswith("<") and bool(LETTER.search(s))


def _is_tr(call) -> bool:
    return isinstance(call.func, ast.Name) and call.func.id in {"tr", "tr_doc"}


def _func_name(call) -> str | None:
    f = call.func
    if isinstance(f, ast.Attribute):
        return f.attr
    if isinstance(f, ast.Name):
        return f.id
    return None


def _is_go(call) -> bool:
    f = call.func
    return isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) and f.value.id == "go"


def collect(tree):
    targets, fstrings = [], []
    parents = {}
    for p in ast.walk(tree):
        for c in ast.iter_child_nodes(p):
            parents[c] = p

    def inside_tr(node):
        p = parents.get(node)
        while p is not None:
            if isinstance(p, ast.Call) and _is_tr(p):
                return True
            p = parents.get(p)
        return False

    for call in ast.walk(tree):
        if not isinstance(call, ast.Call) or _is_tr(call):
            continue
        name = _func_name(call)
        cands = []
        if name in UI_METHODS or name in HELPERS:
            if call.args:
                cands.append(call.args[0])
            if name == "tabs" or (call.args and isinstance(call.args[0], ast.List) and name == "tabs"):
                pass
        if name == "tabs" and call.args and isinstance(call.args[0], (ast.List, ast.Tuple)):
            cands.extend(call.args[0].elts)
        if name == "metric" and len(call.args) >= 3:
            cands.append(call.args[2])
        for kw in call.keywords:
            if kw.arg in TEXT_KWARGS or (kw.arg == "name" and _is_go(call)):
                cands.append(kw.value)
        for c in cands:
            if inside_tr(c):
                continue
            if _wants(c):
                targets.append(c)
            elif isinstance(c, ast.JoinedStr):
                fstrings.append(c)
    return targets, fstrings


def fstring_to_tr(src: str, node: ast.JoinedStr) -> str | None:
    """f"Tekst {x} i {y:.2f}" -> tr("Tekst {x} i {v1}", x=x, v1=f"{y:.2f}").

    Zwraca None, gdy w f-stringu nie ma tekstu do tlumaczenia (np. f"### {title}").
    Stale fragmenty: klamry escapowane ({{ }}), bo tr() uzywa str.format.
    """
    parts, kwargs, names = [], [], {}
    text_only = ""
    for v in node.values:
        if isinstance(v, ast.Constant):
            text_only += v.value
            parts.append(v.value.replace("{", "{{").replace("}", "}}"))
            continue
        expr_src = ast.get_source_segment(src, v.value) or ast.unparse(v.value)
        if v.conversion != -1 or v.format_spec is not None:
            value_src = ast.unparse(ast.JoinedStr([v]))
            key = ("fmt", value_src)
        else:
            value_src = expr_src
            key = ("raw", expr_src)
        if key not in names:
            if isinstance(v.value, ast.Name) and key[0] == "raw" and v.value.id not in names.values():
                pname = v.value.id
            else:
                pname = f"v{len(names)}"
            names[key] = pname
            kwargs.append(f"{pname}={value_src}")
        parts.append("{" + names[key] + "}")
    if not LETTER.search(re.sub(r"[#*_`>\-|]", " ", text_only)):
        return None
    template = "".join(parts)
    lit = repr(template)  # zawsze bezpieczny literal (\n jako escape), klucz katalogu = template
    return f"tr({lit}" + (", " + ", ".join(kwargs) if kwargs else "") + ")"


def convert_fstrings(path: str, dry: bool) -> int:
    src = open(path, encoding="utf-8").read()
    tree = ast.parse(src)
    _, fstrings = collect(tree)
    starts = _offsets(src)

    def off(line, col):
        line_txt = src[starts[line - 1]:starts[line]]
        return starts[line - 1] + len(line_txt.encode("utf-8")[:col].decode("utf-8", "ignore"))

    repl = []
    for n in fstrings:
        new = fstring_to_tr(src, n)
        if new:
            repl.append((off(n.lineno, n.col_offset), off(n.end_lineno, n.end_col_offset), new))
    out = src
    for a, b, new in sorted(set(repl), reverse=True):
        out = out[:a] + new + out[b:]
    if repl and not dry:
        ast.parse(out)
        if not re.search(r"^from components\.i18n import .*\btr\b", out, re.M):
            raise SystemExit(f"{path}: brak importu tr — uruchom najpierw tryb podstawowy")
        open(path, "w", encoding="utf-8").write(out)
    return len(repl)


def _offsets(src: str):
    starts, pos = [0], 0
    for line in src.splitlines(keepends=True):
        pos += len(line)
        starts.append(pos)
    return starts


def wrap_file(path: str, dry: bool) -> tuple[int, list[str]]:
    src = open(path, encoding="utf-8").read()
    tree = ast.parse(src)
    targets, fstrings = collect(tree)
    starts = _offsets(src)

    def off(line, col):  # col_offset w AST to bajty UTF-8
        line_txt = src[starts[line - 1]:starts[line]]
        return starts[line - 1] + len(line_txt.encode("utf-8")[:col].decode("utf-8", "ignore"))

    spans = sorted({(off(n.lineno, n.col_offset), off(n.end_lineno, n.end_col_offset)) for n in targets},
                   reverse=True)
    out = src
    for a, b in spans:
        out = out[:a] + "tr(" + out[a:b] + ")" + out[b:]
    report = [f"{path}:{n.lineno}: f-string: {ast.get_source_segment(src, n)[:110]}" for n in fstrings]
    if spans and not re.search(r"^from components\.i18n import .*\btr\b", out, re.M):
        lines = out.splitlines(keepends=True)
        last_import = 0
        for i, ln in enumerate(lines):
            if re.match(r"(from \S+ import |import )", ln) and not ln.startswith(" "):
                last_import = i
                # import w nawiasach na wiele linii
                if "(" in ln and ")" not in ln:
                    j = i
                    while ")" not in lines[j]:
                        j += 1
                    last_import = j
        lines.insert(last_import + 1, "from components.i18n import tr\n")
        out = "".join(lines)
    if not dry and out != src:
        ast.parse(out)
        open(path, "w", encoding="utf-8").write(out)
    return len(spans), report


if __name__ == "__main__":
    args = sys.argv[1:]
    dry = "--dry" in args
    files = [a for a in args if a not in ("--dry", "--fstrings")]
    if "--fstrings" in args:
        total = 0
        for f in files:
            n = convert_fstrings(f, dry)
            total += n
            print(f"{f}: {n} f-strings -> tr()")
        print("TOTAL", total)
        raise SystemExit(0)
    total = 0
    for f in files:
        n, rep = wrap_file(f, dry)
        total += n
        print(f"{f}: {n} wrapped, {len(rep)} f-strings")
        for r in rep:
            print("   ", r)
    print("TOTAL", total)
