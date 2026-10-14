"""Frases en lenguaje sencillo para las razones a favor y los riesgos (contenido, no lógica).

Cada métrica del score tiene una frase para cuando destaca para bien (percentil ≥ 75 %) y
otra para cuando destaca para mal (≤ 25 %). El dato concreto se añade aparte.
"""

# métrica → (frase si destaca para bien, frase si destaca para mal)
METRIC_TEXTS: dict[str, tuple[str, str]] = {
    "pe_trailing": (
        "Es más barata que su sector: pagas menos por cada euro de beneficio.",
        "Está cara frente a su sector: pagas más por cada euro de beneficio.",
    ),
    "pe_forward": (
        "Con los beneficios que se esperan, también sale más barata que su sector.",
        "Con los beneficios que se esperan, sigue siendo cara frente a su sector.",
    ),
    "peg": (
        "Su precio es bajo para lo que se espera que crezca.",
        "Su precio es alto para lo que se espera que crezca.",
    ),
    "price_to_book": (
        "Cotiza más cerca de lo que vale su patrimonio que sus comparables.",
        "Cotiza muy por encima de lo que vale su patrimonio, más que sus comparables.",
    ),
    "fcf_yield": (
        "Genera mucha caja libre para lo que cuesta.",
        "Genera poca caja libre para lo que cuesta.",
    ),
    "debt_to_equity": (
        "Tiene menos deuda que una empresa típica de su sector.",
        "Tiene más deuda que una empresa típica de su sector.",
    ),
    "fcf_margin": (
        "Convierte en caja una parte de sus ventas mayor que su sector.",
        "Convierte en caja una parte de sus ventas menor que su sector.",
    ),
    "roe": (
        "Gana más por cada euro de sus accionistas que la mayoría de su sector.",
        "Gana menos por cada euro de sus accionistas que la mayoría de su sector.",
    ),
    "operating_margin": (
        "Le queda más margen de cada venta que a sus competidoras.",
        "Le queda menos margen de cada venta que a sus competidoras.",
    ),
    "revenue_growth": (
        "Sus ventas crecen más que las de su sector.",
        "Sus ventas crecen menos (o caen más) que las de su sector.",
    ),
    "earnings_growth": (
        "Su beneficio crece más que el de su sector.",
        "Su beneficio crece menos (o cae más) que el de su sector.",
    ),
    "ret_12m": (
        "Su precio ha subido más que el de la mayoría de valores en el último año.",
        "Su precio se ha quedado atrás frente a la mayoría de valores en el último año.",
    ),
    "ret_6m": (
        "En los últimos 6 meses se ha comportado mejor que la mayoría.",
        "En los últimos 6 meses se ha comportado peor que la mayoría.",
    ),
    "dist_sma200": (
        "Cotiza por encima de su media de 200 sesiones: tendencia de fondo al alza.",
        "Cotiza por debajo de su media de 200 sesiones: tendencia de fondo a la baja.",
    ),
    "vol_1y": (
        "Su precio oscila menos que el de la mayoría: menos sustos.",
        "Su precio oscila más que el de la mayoría: más sustos.",
    ),
    "mdd_1y": (
        "En el último año sus caídas han sido más suaves que las de la mayoría.",
        "En el último año ha llegado a caer más que la mayoría.",
    ),
    "beta": (
        "Se mueve menos que el mercado, tanto cuando sube como cuando baja.",
        "Amplifica los movimientos del mercado, para bien y para mal.",
    ),
    "dividend_yield": (
        "Paga un dividendo más alto que su sector.",
        "Paga menos dividendo que su sector.",
    ),
    "payout_ratio": (
        "Reparte una parte prudente de su beneficio: el dividendo es más sostenible.",
        "Reparte casi todo lo que gana (o más): el dividendo podría recortarse.",
    ),
    # ETFs
    "expense_ratio": (
        "Comisión anual más baja que la de los demás ETFs de referencia.",
        "Comisión anual más alta que la de los demás ETFs de referencia.",
    ),
    "total_assets": (
        "Es de los ETFs más grandes: menos riesgo de cierre y diferencias de precio pequeñas.",
        "Es de los ETFs más pequeños de la lista: algo más de riesgo de cierre.",
    ),
}

# Riesgo propio del sector (claves de sector de Yahoo)
SECTOR_RISKS: dict[str, str] = {
    "Utilities": "Es un sector regulado: cambios en tarifas o impuestos pueden recortar "
    "sus beneficios.",
    "Financial Services": "Depende de los tipos de interés y de la morosidad: una crisis "
    "económica golpea primero a bancos y aseguradoras.",
    "Energy": "Sus beneficios dependen del precio del petróleo y el gas, que no controla.",
    "Basic Materials": "Depende del precio de las materias primas: beneficios muy cíclicos.",
    "Real Estate": "Sensible a los tipos de interés: si suben, su deuda se encarece y sus "
    "inmuebles valen menos.",
    "Technology": "Las valoraciones tecnológicas son exigentes: un mal trimestre puede "
    "castigar mucho el precio.",
    "Healthcare": "Depende de aprobaciones regulatorias y de patentes que caducan.",
    "Consumer Cyclical": "Vende productos que se dejan de comprar en las crisis: beneficios "
    "cíclicos.",
    "Consumer Defensive": "Crece poco: su atractivo es la estabilidad, no el crecimiento.",
    "Industrials": "Depende del ciclo económico y de su cartera de pedidos.",
    "Communication Services": "Sector muy competitivo y con grandes inversiones en redes o "
    "contenidos.",
}

SINGLE_STOCK_RISK = (
    "Una sola empresa concentra el riesgo: lo prudente es repartir entre varias o "
    "combinarla con un ETF."
)


def currency_risk(currency: str) -> str:
    return (
        f"Cotiza en {currency}: si el euro se aprecia, pierdes rentabilidad aunque el "
        "precio no se mueva."
    )


# ETFs: rasgos por papel en la cartera y zona
ETF_ROLE_PROS: dict[str, str] = {
    "core": "Reparte tu dinero entre cientos o miles de empresas: una buena base de cartera.",
    "complement": "Añade una zona o un tipo de empresa que una cartera global apenas tiene.",
    "dividend": "Se centra en empresas que reparten dividendos altos y estables.",
    "bonds": "La renta fija suele amortiguar las caídas de la bolsa.",
    "cash": "Casi no oscila: sirve para aparcar liquidez con un rendimiento parecido al "
    "de los tipos del BCE.",
}
ETF_ACCUMULATING = "Reinvierte los dividendos: en España no tributas por ellos hasta que vendas."
ETF_DISTRIBUTING = "Reparte dividendos: tributan cada año en el IRPF (con retención del 19 %)."
ETF_ZONE_RISKS: dict[str, str] = {
    "EE. UU.": "Concentrado en un solo país (EE. UU.) y, dentro de él, en pocas tecnológicas.",
    "Emergentes": "Los países emergentes oscilan más y tienen más riesgo político y de divisa.",
    "Europa": "Solo invierte en Europa: deja fuera a EE. UU. y Asia.",
    "Eurozona": "Solo invierte en la zona euro.",
}
ETF_GLOBAL_FX_RISK = (
    "Aunque cotiza en euros, invierte sobre todo en empresas de fuera de la zona euro: el "
    "tipo de cambio afecta a su rentabilidad."
)
ETF_BONDS_RATE_RISK = (
    "Si los tipos de interés suben, el precio de los bonos baja (más cuanto más largos)."
)
ETF_CASH_RISK = "Su rentabilidad baja si el BCE baja los tipos, y apenas protege de la inflación."
ETF_NO_TER = "La fuente no da su comisión (TER): consúltala en su KID antes de comprar."
