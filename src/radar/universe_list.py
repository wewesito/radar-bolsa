"""Universo de referencia: empresas con las que se calculan las medianas por sector.

Incluye todo el IBEX 35 y el Mercado Continuo (sección España) y los ETFs de
`radar.etfs`.

No pretende ser "el mercado": es una muestra de grandes empresas líquidas, suficiente para
tener varios comparables por sector en Europa y EE. UU. Revisar la composición una vez al año
(los índices cambian; un ticker que deje de existir simplemente se descarta al construir).
"""

from radar.etfs import ETF_TICKERS

IBEX35 = [
    "ACS.MC",
    "ACX.MC",
    "AENA.MC",
    "AMS.MC",
    "ANA.MC",
    "ANE.MC",
    "BBVA.MC",
    "BKT.MC",
    "CABK.MC",
    "CLNX.MC",
    "COL.MC",
    "ELE.MC",
    "ENG.MC",
    "FDR.MC",
    "FER.MC",
    "GRF.MC",
    "IAG.MC",
    "IBE.MC",
    "IDR.MC",
    "ITX.MC",
    "LOG.MC",
    "MAP.MC",
    "MRL.MC",
    "MTS.MC",
    "NTGY.MC",
    "PUIG.MC",
    "RED.MC",
    "REP.MC",
    "ROVI.MC",
    "SAB.MC",
    "SAN.MC",
    "SCYR.MC",
    "SLR.MC",
    "TEF.MC",
    "UNI.MC",
]

# Euro Stoxx 50 sin los españoles (ya están arriba)
EUROSTOXX50_EX_ES = [
    "ADS.DE",
    "ADYEN.AS",
    "AD.AS",
    "AI.PA",
    "AIR.PA",
    "ALV.DE",
    "ABI.BR",
    "ASML.AS",
    "CS.PA",
    "BAS.DE",
    "BAYN.DE",
    "BMW.DE",
    "BNP.PA",
    "BN.PA",
    "DB1.DE",
    "DHL.DE",
    "DTE.DE",
    "ENEL.MI",
    "ENI.MI",
    "EL.PA",
    "RACE.MI",
    "IFX.DE",
    "INGA.AS",
    "ISP.MI",
    "KER.PA",
    "OR.PA",
    "MC.PA",
    "MBG.DE",
    "MUV2.DE",
    "NOKIA.HE",
    "PRX.AS",
    "RMS.PA",
    "SAF.PA",
    "SAN.PA",
    "SAP.DE",
    "SU.PA",
    "SIE.DE",
    "STLAM.MI",
    "TTE.PA",
    "UCG.MI",
    "DG.PA",
    "VOW3.DE",
    "WKL.AS",
    "SGO.PA",
    "NDA-FI.HE",
]

US_LARGE = [
    "AAPL",
    "MSFT",
    "NVDA",
    "AMZN",
    "GOOGL",
    "META",
    "AVGO",
    "JPM",
    "BAC",
    "WFC",
    "V",
    "MA",
    "JNJ",
    "LLY",
    "PFE",
    "MRK",
    "UNH",
    "XOM",
    "CVX",
    "PG",
    "KO",
    "PEP",
    "WMT",
    "COST",
    "HD",
    "MCD",
    "NKE",
    "DIS",
    "CAT",
    "GE",
    "NEE",
    "DUK",
    "T",
    "VZ",
    "AMT",
    "PLD",
    "LIN",
    "HON",
    "ORCL",
    "CRM",
]

# Refuerzo de sectores con pocas empresas (Energía, Materiales, Inmobiliario): sin al
# menos 5 comparables por sector no se puede calcular una mediana fiable.
SECTOR_FILL = [
    "SHEL.L",
    "BP.L",
    "GALP.LS",
    "COP",
    "SLB",
    "EOG",
    "HEI.DE",
    "SIKA.SW",
    "AKZA.AS",
    "FCX",
    "SHW",
    "NEM",
    "VNA.DE",
    "LI.PA",
    "O",
    "SPG",
    "EQIX",
    "PSA",
]

# Mercado Continuo sin el IBEX 35. Comprobado contra Yahoo el 14/10/2026 (ticker con datos
# y bolsa MCE). Quedan fuera los valores de BME Growth, que Yahoo también marca como MCE,
# y los excluidos de cotización (Catalana Occidente, NH, Lar España, Alba, Borges...).
# Revisar una vez al año: un ticker que deje de existir se descarta al construir.
CONTINUO = [
    "A3M.MC", "ADX.MC", "ADZ.MC", "AEDAS.MC", "AI.MC", "ALM.MC", "ALNT.MC", "AMP.MC",
    "ART.MC", "ATRY.MC", "AZK.MC", "BKY.MC", "CAF.MC", "CASH.MC", "CBAV.MC", "CCEP.MC",
    "CIE.MC", "CIRSA.MC", "CLEO.MC", "COXG.MC", "DIA.MC", "DOM.MC", "EAT.MC", "EBRO.MC",
    "ECR.MC", "EDR.MC", "ENC.MC", "ENER.MC", "ENO.MC", "EZE.MC", "FAE.MC", "FCC.MC",
    "GAM.MC", "GEST.MC", "GRE.MC", "GSJ.MC", "HBX.MC", "HOME.MC", "IBG.MC", "ISUR.MC",
    "LDA.MC", "LGT.MC", "LIB.MC", "MCM.MC", "MDF.MC", "MEL.MC", "MTB.MC", "MVC.MC",
    "NEA.MC", "NTH.MC", "NXT.MC", "OHLA.MC", "OLE.MC", "ORY.MC", "PHM.MC", "PRM.MC",
    "PRS.MC", "PSG.MC", "R4.MC", "REN.MC", "RIO.MC", "RJF.MC", "RLIA.MC", "SOL.MC",
    "SQRL.MC", "TLGO.MC", "TRE.MC", "TRG.MC", "TUB.MC", "UBS.MC", "VID.MC", "VIS.MC",
    "VOC.MC",
]  # fmt: skip

SPAIN = IBEX35 + CONTINUO

STOCKS: list[str] = list(
    dict.fromkeys(IBEX35 + CONTINUO + EUROSTOXX50_EX_ES + US_LARGE + SECTOR_FILL)
)


def spain_index(ticker: str) -> str | None:
    """'IBEX 35', 'Mercado Continuo' o None si no es un valor español del universo."""
    if ticker in IBEX35:
        return "IBEX 35"
    if ticker in CONTINUO:
        return "Mercado Continuo"
    return None


UNIVERSE: list[str] = STOCKS + ETF_TICKERS
