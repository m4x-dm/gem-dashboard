"""Lista linii z polskim tekstem w literalach poza tr()/tr_doc() (narzedzie deweloperskie)."""
import ast, re, sys
PL = re.compile(r"[ąęśłżźćńóĄĘŚŁŻŹĆŃÓ]|\b(?:brak|dane|danych|spolk\w*|zwrot\w*|wynik\w*|sygnal\w*|obligacj\w*|akcj\w*|rynk\w*|wolna|stopa|dodaj|wyczysc|ulubione|kategori\w*|wszystkie|teraz|okres|lat|dni|wartosc\w*|kapital\w*|przychod\w*|zysk\w*|wzrost|spadek|sredni\w*|pobieram|wybierz|porownanie|strategi\w*|portfel\w*|sektor\w*|analityk\w*|dywidend\w*|prognoz\w*|miesiac\w*|tydzien|rok|roku|nazwa|kurs|cena|zmiana|liczba|ile|jak|czy|oraz|dla|nie|tak|jest|sie|na|do|od|po|przez|bez)\b", re.I)
def inside(node, parents, names=("tr","tr_doc")):
    p = parents.get(node)
    while p is not None:
        if isinstance(p, ast.Call) and isinstance(p.func, ast.Name) and p.func.id in names: return True
        p = parents.get(p)
    return False
for path in sys.argv[1:]:
    src = open(path, encoding="utf-8").read(); tree = ast.parse(src)
    parents = {c: p for p in ast.walk(tree) for c in ast.iter_child_nodes(p)}
    docs = set()
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.Module, ast.ClassDef, ast.AsyncFunctionDef)) and n.body and isinstance(n.body[0], ast.Expr) and isinstance(n.body[0].value, ast.Constant):
            docs.add(n.body[0].value)
    seen = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Constant) and isinstance(n.value, str) and n not in docs and not inside(n, parents):
            txt = re.sub(r"<[^>]+>|\{[^}]*\}", " ", n.value)
            txt = re.sub(r"(?:font|margin|padding|border|color|background|display|text|line|letter|white|box)[-\w]*\s*:[^;\"']*;?", " ", txt)
            if PL.search(txt) and n.lineno not in seen:
                seen.add(n.lineno)
                print(f"{path}:{n.lineno}: {n.value.strip()[:100]!r}")
