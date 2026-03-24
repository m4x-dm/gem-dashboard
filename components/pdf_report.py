"""Generator raportu PDF — tekstowo-tabelaryczny (bez wykresow)."""

import io
import platform
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, black, white
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


# --- Kolory ---
GOLD = HexColor("#C9A84C")
BG_DARK = HexColor("#0B0E1A")
GREEN = HexColor("#22C55E")
RED = HexColor("#EF4444")
GRAY = HexColor("#6B7280")
LIGHT_BG = HexColor("#F8F9FA")


def _register_font():
    """Rejestruje font z obsluga polskich znakow."""
    if platform.system() == "Windows":
        try:
            pdfmetrics.registerFont(TTFont("ReportFont", r"C:\Windows\Fonts\arial.ttf"))
            pdfmetrics.registerFont(TTFont("ReportFont-Bold", r"C:\Windows\Fonts\arialbd.ttf"))
            return "ReportFont"
        except Exception:
            pass
    # Fallback: Helvetica (bez polskich diakrytykow)
    return "Helvetica"


def _fmt_pct(val, decimals=2):
    """Formatuje wartosc jako procent."""
    if val is None:
        return "—"
    try:
        v = float(val) * 100
        sign = "+" if v > 0 else ""
        return f"{sign}{v:.{decimals}f}%"
    except (ValueError, TypeError):
        return "—"


def generate_report(sections: dict) -> bytes:
    """Generuje raport PDF z wybranymi sekcjami.

    Args:
        sections: dict z kluczami:
            "gem_signal": dict z gem_classic_signal()
            "regime": dict {"label": str, "score": float}
            "top_etfs": list of (ticker, name, score)
            "sparklines": list of (ticker, label, price, change_1m)
            "backtest_stats": dict {strategy_name: {CAGR, Max Drawdown, Sharpe, ...}}
            "ranking_top10": list of (ticker, name, score, mom_abs)
            "macro": list of (name, value, unit, signal)

    Returns:
        bytes — zawartosc PDF
    """
    buf = io.BytesIO()
    font_name = _register_font()
    bold_name = f"{font_name}-Bold" if font_name != "Helvetica" else "Helvetica-Bold"

    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=20 * mm, rightMargin=20 * mm,
        topMargin=15 * mm, bottomMargin=15 * mm,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "ReportTitle", parent=styles["Title"],
        fontName=bold_name, fontSize=20, textColor=GOLD,
        alignment=TA_CENTER, spaceAfter=6,
    )
    subtitle_style = ParagraphStyle(
        "ReportSubtitle", parent=styles["Normal"],
        fontName=font_name, fontSize=10, textColor=GRAY,
        alignment=TA_CENTER, spaceAfter=20,
    )
    heading_style = ParagraphStyle(
        "ReportH2", parent=styles["Heading2"],
        fontName=bold_name, fontSize=14, textColor=GOLD,
        spaceBefore=16, spaceAfter=8,
    )
    body_style = ParagraphStyle(
        "ReportBody", parent=styles["Normal"],
        fontName=font_name, fontSize=10, textColor=black,
        spaceAfter=6, leading=14,
    )
    small_style = ParagraphStyle(
        "ReportSmall", parent=styles["Normal"],
        fontName=font_name, fontSize=8, textColor=GRAY,
        alignment=TA_CENTER, spaceBefore=12,
    )

    elements = []

    # ---- NAGLOWEK ----
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    elements.append(Paragraph("GEM ETF Dashboard — Raport", title_style))
    elements.append(Paragraph(f"Wygenerowano: {now}", subtitle_style))

    # ---- SYGNAL GEM ----
    if "gem_signal" in sections:
        gem = sections["gem_signal"]
        elements.append(Paragraph("Sygnal GEM", heading_style))
        signal = gem.get("signal", "—")
        label = gem.get("signal_label", "")
        elements.append(Paragraph(f"<b>Aktualny sygnal: {signal}</b>", body_style))
        elements.append(Paragraph(label, body_style))

        # Zwroty 12M
        data = [
            ["Instrument", "Zwrot 12M"],
            ["QQQ (USA)", _fmt_pct(gem.get("qqq_12m"))],
            ["VEA (Rozwin.)", _fmt_pct(gem.get("vea_12m"))],
            ["EEM (Wsch.)", _fmt_pct(gem.get("eem_12m"))],
            ["ACWI (Global)", _fmt_pct(gem.get("acwi_12m"))],
            ["AGG (Obligacje)", _fmt_pct(gem.get("agg_12m"))],
        ]
        t = Table(data, colWidths=[120, 80])
        t.setStyle(_table_style())
        elements.append(t)
        elements.append(Spacer(1, 8))

    # ---- REGIME ----
    if "regime" in sections:
        reg = sections["regime"]
        elements.append(Paragraph("Regime rynkowy", heading_style))
        elements.append(Paragraph(
            f"<b>{reg.get('label', '—')}</b> (Risk-On score: {reg.get('score', 0):.0f}%)",
            body_style,
        ))
        elements.append(Spacer(1, 8))

    # ---- TOP 5 ETF ----
    if "top_etfs" in sections and sections["top_etfs"]:
        elements.append(Paragraph("Top 5 ETF-ow wg momentum", heading_style))
        data = [["#", "Ticker", "Nazwa", "Wynik"]]
        for i, (ticker, name, score) in enumerate(sections["top_etfs"][:5], 1):
            data.append([str(i), ticker, name, _fmt_pct(score)])
        t = Table(data, colWidths=[25, 60, 180, 80])
        t.setStyle(_table_style())
        elements.append(t)
        elements.append(Spacer(1, 8))

    # ---- SPARKLINES (tabela aktywow) ----
    if "sparklines" in sections and sections["sparklines"]:
        elements.append(Paragraph("Kluczowe aktywa", heading_style))
        data = [["Ticker", "Aktywo", "Cena", "Zmiana 1M"]]
        for ticker, label, price, chg in sections["sparklines"]:
            data.append([ticker, label, f"{price:,.2f}", _fmt_pct(chg)])
        t = Table(data, colWidths=[60, 120, 80, 80])
        t.setStyle(_table_style())
        elements.append(t)
        elements.append(Spacer(1, 8))

    # ---- BACKTEST STATS ----
    if "backtest_stats" in sections and sections["backtest_stats"]:
        elements.append(Paragraph("Statystyki strategii (5 lat)", heading_style))
        data = [["Strategia", "CAGR", "Max DD", "Sharpe"]]
        for name, s in sections["backtest_stats"].items():
            data.append([
                name,
                _fmt_pct(s.get("CAGR")),
                _fmt_pct(s.get("Max Drawdown")),
                f"{s.get('Sharpe', 0):.2f}",
            ])
        t = Table(data, colWidths=[120, 70, 70, 60])
        t.setStyle(_table_style())
        elements.append(t)
        elements.append(Spacer(1, 8))

    # ---- RANKING TOP 10 ----
    if "ranking_top10" in sections and sections["ranking_top10"]:
        elements.append(Paragraph("Ranking ETF — Top 10", heading_style))
        data = [["#", "Ticker", "Nazwa", "Wynik", "Mom. abs."]]
        for i, (ticker, name, score, mom) in enumerate(sections["ranking_top10"][:10], 1):
            data.append([str(i), ticker, name, _fmt_pct(score), mom])
        t = Table(data, colWidths=[25, 55, 160, 70, 60])
        t.setStyle(_table_style())
        elements.append(t)
        elements.append(Spacer(1, 8))

    # ---- MAKRO ----
    if "macro" in sections and sections["macro"]:
        elements.append(Paragraph("Makro Dashboard", heading_style))
        data = [["Wskaznik", "Wartosc", "Sygnal"]]
        for name, value, unit, signal in sections["macro"]:
            data.append([name, f"{value} {unit}", signal])
        t = Table(data, colWidths=[120, 100, 100])
        t.setStyle(_table_style())
        elements.append(t)
        elements.append(Spacer(1, 8))

    # ---- STOPKA ----
    elements.append(Spacer(1, 20))
    elements.append(Paragraph(
        "Dashboard ma charakter edukacyjny i informacyjny. Nie stanowi porady inwestycyjnej. "
        "Wyniki historyczne nie gwarantuja przyszlych zwrotow.",
        small_style,
    ))
    elements.append(Paragraph(f"© 2026 M4X · GEM ETF Dashboard", small_style))

    doc.build(elements)
    buf.seek(0)
    return buf.read()


def _table_style():
    """Standardowy styl tabeli raportu."""
    return TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), GOLD),
        ("TEXTCOLOR", (0, 0), (-1, 0), white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("ALIGN", (-1, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.5, GRAY),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, LIGHT_BG]),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ])
