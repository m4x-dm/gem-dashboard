"""Strona 6: O strategii GEM — opis po polsku."""

import streamlit as st
from components.sidebar import setup_sidebar, render_footer

st.set_page_config(page_title="O strategii GEM", page_icon="📚", layout="wide")
setup_sidebar()

st.markdown("# 📚 O strategii GEM")

st.markdown("""
## Czym jest GEM?

**Global Equity Momentum (GEM)** to strategia inwestycyjna opracowana przez **Gary'ego Antonacciego**,
opisana w ksiazce *"Dual Momentum Investing"* (2014). Laczy dwa rodzaje momentum:

### 1. Momentum absolutny (Absolute Momentum)
- Porownuje zwrot aktywa z **bezpieczna stopa wolna od ryzyka** (np. T-bill)
- Jesli zwrot 12M (skip-month) > stopa wolna → **trend wzrostowy**, warto inwestowac
- Jesli zwrot 12M (skip-month) < stopa wolna → **trend spadkowy**, lepiej przeniesc sie do obligacji
- **Skip-month (12-1):** zwrot 12M jest liczony od 13 mies. wstecz do 1 mies. wstecz, pomijajac ostatni miesiac (eliminuje efekt krotkoterminowej rewersji — Jegadeesh & Titman 1993)

### 2. Momentum relatywny (Relative Momentum)
- Porownuje zwroty **dwoch (lub wiecej) aktywow** miedzy soba
- Inwestujesz w aktywo z **wyzszym momentum** (wyzszym zwrotem w danym okresie)
- W klasycznym GEM: porownanie USA (QQQ) vs rynki rozw. (VEA) vs rynki wsch. (EEM) vs swiat (ACWI)

---

## Jak dziala klasyczny GEM?

Strategia podejmuje decyzje raz w miesiacu w 3 krokach:

| Krok | Warunek | Akcja |
|------|---------|-------|
| 1 | Zwrot QQQ 12M (skip-month) < stopa wolna | → Kup obligacje (AGG) |
| 2 | Porownaj QQQ vs VEA vs EEM vs ACWI | → Kup aktywo z najwyzszym 12M momentum |

**Zawsze jestes w 100% w jednym aktywie** — to strategia typu "all-in/all-out".
Porownywane sa 4 rynki akcji: USA (QQQ), rozw. (VEA), wsch. (EEM), swiat (ACWI).

---

## Rozszerzony GEM w tym dashboardzie

Ten dashboard rozszerza klasyczny GEM o **30+ ETF-ow** z 7 kategorii:
- Akcje USA, rynki rozw., rynki wsch., obligacje, zloto, REIT, sektory

### Wynik kompozytowy
Kazdy ETF otrzymuje wynik na podstawie wazonej sredniej zwrotow:

```
Wynik = 12M (skip-month) × 50% + 6M × 25% + 3M × 15% + 1M × 10%
```

Wagi faworyzuja **dlugookresowy trend** (12M = 50%), ale uwzgledniaja tez krotsze okresy.
12M uzywa metody **skip-month (12-1)** — pomija ostatni miesiac, zeby uniknac efektu rewersji.

---

## Jak czytac sygnaly?

### Momentum absolutny: TAK / NIE
- **TAK** = zwrot 12M (skip-month) > stopa wolna → trend wzrostowy, warto rozwazyc
- **NIE** = zwrot 12M (skip-month) < stopa wolna → trend spadkowy, ostroznosc

### Wynik kompozytowy
- **Wyzszy wynik = silniejszy trend wzrostowy**
- Ujemny wynik = trend spadkowy w wiekszosci okresow

### Sygnal GEM (klasyczny)
- 🟢 **QQQ** = akcje USA dominuja
- 🔵 **VEA** = rynki rozw. dominuja
- 🟣 **EEM** = rynki wschodzace dominuja
- 🌐 **ACWI** = rynek globalny dominuje
- 🟡 **AGG** = rynek w trendzie spadkowym, schron w obligacjach

---

## Zalety strategii GEM

- **Prosta** — wystarczy decyzja raz w miesiacu
- **Systematyczna** — eliminuje emocje z inwestowania
- **Historyczne wyniki** — w backtestach wyzsza stopa zwrotu niz buy&hold przy nizszym drawdownie
- **Dywersyfikacja** — przechodzi miedzy klasami aktywow w zaleznosci od trendu
- **Ochrona przed bessami** — momentum absolutny sygnalizuje trend spadkowy i przenosi do obligacji

## Wady i ograniczenia

- **Opoznione sygnaly** — oparty na danych 12M, reaguje z opoznieniem
- **Whipsaws** — moze generowac falszywe sygnaly w rynku bocznym
- **Brak dywersyfikacji** — klasyczny GEM trzyma 100% w jednym aktywie
- **Koszty transakcji** — czeste zmiany sygnalu = prowizje + podatki
- **Przeszle wyniki ≠ przyszle** — backtesty nie gwarantuja przyszlych zyskow

---

## Zrodla

- **Gary Antonacci** — *Dual Momentum Investing* (2014, McGraw-Hill)
- [OptimalMomentum.com](https://www.optimalmomentum.com/) — strona autora
- **Jegadeesh & Titman (1993)** — "Returns to Buying Winners and Selling Losers" — fundament akademicki momentum
- **Asness et al. (2014)** — "Fact, Fiction and Momentum Investing" — AQR Capital

---

> **Wazne:** Ten dashboard sluzy wylacznie celom edukacyjnym. Nie jest to rekomendacja inwestycyjna.
> Przed podjęciem decyzji inwestycyjnych skonsultuj sie z licencjonowanym doradca finansowym.
""")

render_footer()
