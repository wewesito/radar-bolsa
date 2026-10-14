"""Control de calidad de los precios descargados (funciones puras).

Yahoo trae a veces precios corruptos (saltos de miles de %, ceros). Se revisa el último año de
cierres: un salto diario por debajo de -60 % o por encima de +100 %, o un precio no positivo,
se marca como sospechoso. Un valor con datos sospechosos nunca sale como «Comprar».
"""

import pandas as pd

MAX_DAILY_DROP = -0.60
MAX_DAILY_RISE = 1.00
CHECK_DAYS = 260  # sesiones revisadas (≈ 1 año)


def price_warning(close: pd.Series) -> str | None:
    """Texto de aviso si el último año de cierres tiene datos imposibles; None si está bien."""
    recent = close.dropna().iloc[-CHECK_DAYS:]
    if recent.empty:
        return None
    if (recent <= 0).any():
        return "Hay precios cero o negativos en su histórico: la fuente puede tener un error."
    moves = recent.pct_change().dropna()
    bad = moves[(moves < MAX_DAILY_DROP) | (moves > MAX_DAILY_RISE)]
    if bad.empty:
        return None
    day = bad.abs().idxmax()
    pct = f"{bad[day] * 100:+,.0f}".replace(",", ".")
    return (
        f"Salto de precio sospechoso ({pct} % en un día, el {pd.Timestamp(day):%d/%m/%Y}): "
        "puede ser un error de la fuente, así que sus indicadores no son fiables."
    )
