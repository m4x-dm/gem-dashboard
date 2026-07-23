"""Universum 140 spolek GPW z polskimi nazwami i indeksami (WIG20, mWIG40, sWIG80).

Sklad indeksow zweryfikowany 2026-07-23 wg biznesradar.pl:
- WIG20  = 20 spolek
- mWIG40 = 40 spolek
- sWIG80 = 80 spolek

Ostatnie waznieksze zmiany skladow:
- 20.03.2026: TPE (Tauron) zastapil OPL (Orange) w WIG20
- IV.2026:    SPL (Santander Bank Polska) rename -> EBP (Erste Bank Polska)
- X.2024:     ZAB (Zabka) debiut, dodana do WIG20
- 2023:       Kernel (KER), Huuuge (jako HRS), Kogeneracja (KGN) i inne wycofane
- 2024:       Modivo (MDV) i Pepco (PCO) w WIG20; nowe m/sWIG (Diagnostyka, Newag, Vercom itp.)
"""

GPW_CATEGORIES = {
    "WIG20": {
        "ALE.WA": "Allegro",
        "ALR.WA": "Alior Bank",
        "BDX.WA": "Budimex",
        "CDR.WA": "CD Projekt",
        "DNP.WA": "Dino Polska",
        "EBP.WA": "Erste Bank Polska",  # ex-Santander (SPL), rename IV.2026
        "KGH.WA": "KGHM Polska Miedz",
        "KRU.WA": "Kruk",
        "KTY.WA": "Grupa Kety",
        "LPP.WA": "LPP",
        "MBK.WA": "mBank",
        "MDV.WA": "Modivo",
        "PCO.WA": "Pepco Group",
        "PEO.WA": "Bank Pekao",
        "PGE.WA": "PGE Polska Grupa Energetyczna",
        "PKN.WA": "Orlen",
        "PKO.WA": "PKO Bank Polski",
        "PZU.WA": "PZU",
        "TPE.WA": "Tauron Polska Energia",  # dodany 20.03.2026 zamiast OPL
        "ZAB.WA": "Zabka Group",
    },
    "mWIG40": {
        "ABE.WA": "AB",
        "ACP.WA": "Asseco Poland",
        "APR.WA": "Auto Partner",
        "ASB.WA": "ASBISc Enterprises",
        "ASE.WA": "Asseco South Eastern Europe",
        "ATT.WA": "Grupa Azoty",
        "BFT.WA": "Benefit Systems",
        "BHW.WA": "Bank Handlowy",
        "BNP.WA": "BNP Paribas Bank Polska",
        "CAR.WA": "Inter Cars",
        "CBF.WA": "cyber_Folks",
        "CPS.WA": "Cyfrowy Polsat",
        "CRI.WA": "Creotech Instruments",
        "DIA.WA": "Diagnostyka",
        "DOM.WA": "Dom Development",
        "DVL.WA": "Develia",
        "EAT.WA": "AmRest Holdings",
        "ENA.WA": "Enea",
        "GPP.WA": "Grupa Pracuj",
        "GPW.WA": "GPW",
        "ING.WA": "ING Bank Slaski",
        "JSW.WA": "Jastrzebska Spolka Weglowa",
        "LBW.WA": "Lubawa",
        "MBR.WA": "Mo-Bruk",
        "MIL.WA": "Bank Millennium",
        "MRB.WA": "Mirbud",
        "MUR.WA": "Murapol",
        "NEU.WA": "Neuca",
        "NWG.WA": "Newag",
        "OPL.WA": "Orange Polska",
        "PEP.WA": "Polenergia",
        "PXM.WA": "Polimex Mostostal",
        "RBW.WA": "Rainbow Tours",
        "SNT.WA": "Synektik",
        "TEN.WA": "Ten Square Games",
        "TXT.WA": "Text (ex-LiveChat)",
        "VOX.WA": "Voxel",
        "VRC.WA": "Vercom",
        "WPL.WA": "Wirtualna Polska Holding",
        "XTB.WA": "XTB",
    },
    "sWIG80": {
        "11B.WA": "11 bit studios",
        "1AT.WA": "Atal",
        "ABS.WA": "Asseco Business Solutions",
        "AGO.WA": "Agora",
        "AMB.WA": "Ambra",
        "AMC.WA": "Amica Wronki",
        "ANR.WA": "Answear.com",
        "APT.WA": "Apator",
        "ARH.WA": "Archicom",
        "ARL.WA": "Arlen",
        "AST.WA": "Astarta Holding",
        "ATC.WA": "Arctic Paper",
        "ATR.WA": "Atrem",
        "BCX.WA": "Bioceltix",
        "BIO.WA": "Bioton",
        "BLO.WA": "Bloober Team",
        "BMC.WA": "Bumech",
        "BOS.WA": "Bank Ochrony Srodowiska",
        "BRS.WA": "Boryszew",
        "CIG.WA": "CI Games",
        "CLN.WA": "Celon Pharma",
        "CMP.WA": "Comp",
        "COG.WA": "Cognor",
        "CRJ.WA": "Creepy Jar",
        "CRQ.WA": "Creotech Quantum",
        "CTX.WA": "Captor Therapeutics",
        "DAD.WA": "Dadelo",
        "DAT.WA": "Datawalk",
        "DCR.WA": "Decora",
        "DIG.WA": "Digital Network",
        "ECH.WA": "Echo Investment",
        "ELT.WA": "Elektrotim",
        "ENT.WA": "Enter Air",
        "ERB.WA": "Erbud",
        "EUR.WA": "Eurocash",
        "FRO.WA": "Ferro",
        "FTE.WA": "Fabryki Mebli Forte",
        "GRX.WA": "GreenX Metals",
        "HUG.WA": "Huuuge",
        "ICE.WA": "Medinice",
        "KGN.WA": "Kogeneracja",
        "LWB.WA": "Lubelski Wegiel Bogdanka",
        "MCI.WA": "MCI Capital",
        "MDG.WA": "Medicalgorithmics",
        "MLG.WA": "MLP Group",
        "MNC.WA": "Mennica Polska",
        "MRC.WA": "Mercator Medical",
        "MSZ.WA": "Mostostal Zabrze",
        "OND.WA": "Onde",
        "OPN.WA": "Oponeo.pl",
        "PCR.WA": "PCC Rokita",
        "PLW.WA": "PlayWay",
        "QRS.WA": "Quercus TFI",
        "REX.WA": "Rex Concepts",
        "ROB.WA": "Robyg",
        "RVU.WA": "Ryvu Therapeutics",
        "SCP.WA": "Scope Fluidics",
        "SCW.WA": "Scanway",
        "SEL.WA": "Selena FM",
        "SGN.WA": "Sygnity",
        "SHO.WA": "Shoper",
        "SKA.WA": "Sniezka",
        "SLV.WA": "Selvita",
        "SNK.WA": "Sanok Rubber Company",
        "STP.WA": "Stalprodukt",
        "STX.WA": "Stalexport Autostrady",
        "SVE.WA": "Synthaverse",
        "TAR.WA": "Tarczynski",
        "TOA.WA": "Toya",
        "TOR.WA": "Torpol",
        "UNI.WA": "Unibep",
        "UNT.WA": "Unimot",
        "VGO.WA": "Vigo Photonics",
        "VOT.WA": "Votum",
        "VRG.WA": "VRG (Vistula Retail Group)",
        "WLT.WA": "Wielton",
        "WTN.WA": "Wittchen",
        "WWL.WA": "Wawel",
        "ZEP.WA": "ZE PAK",
        "ZRE.WA": "Zremb-Chojnice",
    },
}

# Flat dict: ticker -> nazwa PL
GPW_NAMES: dict[str, str] = {}
# Flat dict: ticker -> indeks (WIG20/mWIG40/sWIG80)
GPW_CATEGORY_MAP: dict[str, str] = {}

for category, stocks in GPW_CATEGORIES.items():
    for ticker, name in stocks.items():
        GPW_NAMES[ticker] = name
        GPW_CATEGORY_MAP[ticker] = category

ALL_GPW_TICKERS = list(GPW_NAMES.keys())

# Banki GPW — banki nie raportuja klasycznego EBITDA / EV/EBITDA / FCF.
# yfinance czesto zwraca None dla tych metryk dla bankow.
# Tab "Finanse spolki" auto-hide te wskazniki gdy is_bank(ticker) == True.
# Last verified: 2026-07-23
GPW_BANKS: set[str] = {
    # WIG20
    "ALR.WA",   # Alior Bank
    "EBP.WA",   # Erste Bank Polska (ex-Santander SPL)
    "MBK.WA",   # mBank
    "PEO.WA",   # Bank Pekao
    "PKO.WA",   # PKO Bank Polski
    # mWIG40
    "BHW.WA",   # Bank Handlowy
    "BNP.WA",   # BNP Paribas Bank Polska
    "ING.WA",   # ING Bank Slaski
    "MIL.WA",   # Bank Millennium
    # sWIG80
    "BOS.WA",   # Bank Ochrony Srodowiska
}


def get_gpw_universe() -> list[str]:
    """Splaszczona lista tickerow GPW z `GPW_CATEGORIES`.

    `GPW_CATEGORIES` to dict {indeks: {ticker: nazwa}} (WIG20/mWIG40/sWIG80).
    Zwraca posortowana liste 140 tickerow z sufiksem .WA, bez duplikatow.
    """
    tickers: list[str] = []
    for index_dict in GPW_CATEGORIES.values():
        tickers.extend(index_dict.keys())
    return sorted(set(tickers))
