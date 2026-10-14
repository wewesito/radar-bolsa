"""Glosario: qué es cada métrica, cómo se calcula, cómo leerla y sus limitaciones.

Es contenido (datos), no lógica. Un test comprueba que toda métrica del catálogo
(`fundamentals.metrics.ALL_METRICS`) tiene su entrada aquí.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Entry:
    key: str
    term: str
    category: str
    what: str
    formula: str
    reading: str  # qué se suele considerar "bueno" o "malo" (siempre con matices)
    limits: str


ENTRIES: list[Entry] = [
    # --- Tamaño y valoración ---------------------------------------------------------
    Entry(
        "market_cap",
        "Capitalización bursátil",
        "Valoración",
        "Lo que vale la empresa en bolsa: el precio de todas sus acciones juntas.",
        "Precio por acción × número de acciones.",
        "No es buena ni mala: indica el tamaño. Las grandes (más de 10.000 M€) suelen ser "
        "más estables y líquidas; las pequeñas pueden crecer más, pero con más riesgo.",
        "No incluye la deuda. Para comparar el valor de dos negocios con deudas muy distintas "
        "se usa el valor empresa (capitalización + deuda neta).",
    ),
    Entry(
        "pe_trailing",
        "PER (Price/Earnings Ratio)",
        "Valoración",
        "Cuántas veces pagas el beneficio anual de la empresa. Un PER de 15 equivale a "
        "pagar 15 años del beneficio actual.",
        "Precio por acción / beneficio por acción (BPA) de los últimos 12 meses.",
        "Más bajo = más barato respecto a lo que gana. Históricamente, la media del mercado "
        "ronda 15-20, pero varía mucho por sector: los bancos suelen cotizar a 6-12 y las "
        "tecnológicas a 25 o más. Compáralo siempre con el sector y con su propia historia.",
        "Un PER bajo puede ser una trampa: la empresa puede estar barata porque el mercado "
        "espera que su beneficio caiga. Con pérdidas no tiene sentido (no se muestra). Los "
        "beneficios extraordinarios (venta de un negocio) lo distorsionan.",
    ),
    Entry(
        "pe_forward",
        "PER estimado (forward)",
        "Valoración",
        "Como el PER, pero con el beneficio que los analistas esperan para los próximos 12 meses.",
        "Precio / BPA estimado a 12 meses.",
        "Si es menor que el PER actual, los analistas esperan que el beneficio crezca.",
        "Depende de previsiones, que a menudo fallan y suelen ser optimistas.",
    ),
    Entry(
        "peg",
        "PEG",
        "Valoración",
        "PER ajustado por el crecimiento: si una empresa crece mucho, es razonable que tenga "
        "un PER más alto.",
        "PER / crecimiento anual esperado del beneficio (en %). PER 20 y crecimiento del 20 % "
        "→ PEG 1.",
        "Popularmente: < 1 se lee como 'barato para lo que crece' y > 2 como 'caro'.",
        "Es tan bueno como la estimación de crecimiento, que es muy incierta. Con crecimiento "
        "negativo o casi nulo, el PEG no tiene sentido.",
    ),
    Entry(
        "price_to_book",
        "Precio / valor contable (P/VC)",
        "Valoración",
        "Cuánto pagas respecto al patrimonio neto que figura en el balance.",
        "Capitalización / patrimonio neto.",
        "Muy útil en bancos y aseguradoras, cuyo negocio es su balance: un P/VC < 1 indica que "
        "cotizan por debajo de su valor en libros.",
        "Poco útil en empresas cuyo valor está en activos intangibles (marcas, software, "
        "patentes) que apenas aparecen en el balance.",
    ),
    Entry(
        "fcf_yield",
        "Rentabilidad por flujo de caja libre (FCF yield)",
        "Valoración",
        "Cuánto efectivo libre genera la empresa por cada euro que cuesta en bolsa. Es como "
        "un 'PER al revés', pero con caja en lugar de beneficio contable.",
        "Flujo de caja libre anual / capitalización.",
        "Más alto = más barato respecto a la caja que genera. Un 5 % o más suele considerarse "
        "atractivo en empresas maduras.",
        "El flujo de caja de un solo año puede ser engañoso (inversiones puntuales). No tiene "
        "sentido en bancos.",
    ),
    Entry(
        "eps_trailing",
        "BPA (beneficio por acción, EPS)",
        "Valoración",
        "El beneficio neto que corresponde a cada acción.",
        "Beneficio neto / número de acciones.",
        "Lo importante es su evolución: que crezca año a año. Su valor absoluto no se "
        "compara entre empresas (depende de cuántas acciones haya emitido cada una).",
        "Las recompras de acciones aumentan el BPA aunque el beneficio total no crezca.",
    ),
    # --- Rentabilidad ------------------------------------------------------------------
    Entry(
        "gross_margin",
        "Margen bruto",
        "Rentabilidad",
        "Qué parte de cada euro vendido queda después de pagar lo que cuesta fabricar o "
        "comprar el producto.",
        "(Ventas − coste de las ventas) / ventas.",
        "Márgenes altos y estables (software > 70 %, lujo > 60 %) suelen indicar poder de "
        "precios o ventaja competitiva. Comparar dentro del sector: un supermercado vive con "
        "márgenes del 25 %.",
        "No aplica a bancos ni aseguradoras.",
    ),
    Entry(
        "operating_margin",
        "Margen operativo (EBIT)",
        "Rentabilidad",
        "Lo que gana el negocio en sí, antes de intereses e impuestos.",
        "Beneficio operativo / ventas.",
        "Por encima del 15 % suele considerarse alto en la mayoría de sectores. Más útil que "
        "el neto para comparar empresas con deudas distintas.",
        "Una empresa puede subirlo temporalmente recortando inversión en I+D o marketing.",
    ),
    Entry(
        "profit_margin",
        "Margen neto",
        "Rentabilidad",
        "Lo que queda de cada euro vendido después de todo: costes, intereses e impuestos.",
        "Beneficio neto / ventas.",
        "Depende muchísimo del sector (distribución 2-5 %, software 20-30 %).",
        "Lo afectan partidas extraordinarias y diferencias fiscales entre países.",
    ),
    Entry(
        "roe",
        "ROE (rentabilidad sobre el patrimonio)",
        "Rentabilidad",
        "Cuánto beneficio obtiene la empresa con el dinero de sus accionistas.",
        "Beneficio neto / patrimonio neto.",
        "Un ROE sostenido por encima del 15 % suele indicar un buen negocio.",
        "La deuda lo infla: si una empresa se endeuda mucho, su patrimonio es pequeño y el ROE "
        "sale alto. Míralo siempre junto a la deuda/patrimonio. Las recompras también lo suben.",
    ),
    # --- Crecimiento -------------------------------------------------------------------
    Entry(
        "revenue_growth",
        "Crecimiento de las ventas",
        "Crecimiento",
        "Cuánto han aumentado los ingresos.",
        "Ventas del último trimestre / ventas del mismo trimestre del año anterior − 1.",
        "Crecer por encima de la inflación y del sector es buena señal. El crecimiento de las "
        "ventas es más difícil de 'maquillar' que el del beneficio.",
        "Un solo trimestre es ruidoso: adquisiciones, efecto divisa o un trimestre "
        "excepcional lo distorsionan. Mira la tendencia de varios años en los informes.",
    ),
    Entry(
        "earnings_growth",
        "Crecimiento del beneficio",
        "Crecimiento",
        "Cuánto ha aumentado el beneficio neto.",
        "Beneficio del último trimestre / mismo trimestre del año anterior − 1.",
        "Lo ideal es que acompañe al de las ventas (crecimiento 'sano').",
        "Muy volátil: partidas extraordinarias pueden dar +200 % o −80 % sin que cambie el "
        "negocio.",
    ),
    # --- Salud financiera ------------------------------------------------------------------
    Entry(
        "debt_to_equity",
        "Deuda / patrimonio",
        "Salud financiera",
        "Cuánta deuda tiene la empresa por cada euro de patrimonio de sus accionistas.",
        "Deuda financiera total / patrimonio neto.",
        "Por debajo de 1 suele considerarse prudente; por encima de 2, elevado, salvo en "
        "sectores con ingresos muy estables y regulados (eléctricas, autopistas).",
        "No aplica a bancos (su 'deuda' son los depósitos de los clientes). No tiene en cuenta "
        "la caja disponible: la deuda neta (deuda − caja) es más precisa.",
    ),
    Entry(
        "fcf_margin",
        "Margen de flujo de caja libre",
        "Salud financiera",
        "Qué parte de las ventas se convierte en dinero disponible después de mantener e "
        "invertir en el negocio.",
        "Flujo de caja libre / ventas.",
        "Positivo y estable es buena señal; negativo de forma continuada obliga a endeudarse "
        "o a ampliar capital.",
        "Una empresa en fuerte expansión puede tenerlo negativo a propósito.",
    ),
    Entry(
        "free_cash_flow",
        "Flujo de caja libre (FCF)",
        "Salud financiera",
        "El dinero real que genera el negocio después de pagar sus inversiones. Con él se "
        "pagan dividendos, se recompran acciones o se reduce deuda.",
        "Flujo de caja operativo − inversiones en activos (capex).",
        "Que sea positivo y crezca es de lo más importante en una empresa madura: el "
        "beneficio contable se puede maquillar, la caja es más difícil.",
        "Varía mucho de un año a otro según el calendario de inversiones.",
    ),
    # --- Dividendo y riesgo ----------------------------------------------------------------
    Entry(
        "dividend_yield",
        "Rentabilidad por dividendo",
        "Dividendo",
        "Qué porcentaje del precio recibes cada año en dividendos.",
        "Dividendo anual por acción / precio.",
        "Entre el 2 % y el 5 % es habitual en empresas maduras. Las que no reparten no son "
        "peores: pueden reinvertir todo para crecer.",
        "Una rentabilidad muy alta (> 8 %) suele ser una señal de alarma: el precio ha caído "
        "porque el mercado espera un recorte del dividendo. Fiscalmente, el dividendo tributa "
        "al cobrarlo.",
    ),
    Entry(
        "beta",
        "Beta",
        "Riesgo",
        "Cuánto tiende a moverse la acción cuando se mueve el mercado.",
        "Covarianza de los rendimientos de la acción y del índice / varianza del índice. "
        "(Yahoo la calcula con 5 años de datos mensuales frente al S&P 500.)",
        "Beta 1 = se mueve como el mercado; 1,5 = amplifica sus movimientos un 50 %; 0,5 = "
        "los suaviza. Las eléctricas suelen tener betas bajas y las tecnológicas, altas.",
        "Mide solo el riesgo ligado al mercado, no el propio de la empresa (un fraude, una "
        "multa...). Cambia con el tiempo.",
    ),
    # --- ETFs ----------------------------------------------------------------------------------
    Entry(
        "expense_ratio",
        "Comisión total (TER)",
        "ETFs",
        "El coste anual que el fondo descuenta de tu inversión, sin que lo veas cobrado.",
        "Gastos anuales del fondo / patrimonio medio.",
        "En ETFs indexados de grandes índices, 0,05 %-0,25 % es lo normal. Por encima del "
        "0,5 % conviene preguntarse qué se paga.",
        "No incluye todo: la comisión de compraventa del bróker o la diferencia entre "
        "precio de compra y de venta (horquilla) también cuestan.",
    ),
    Entry(
        "total_assets",
        "Patrimonio del fondo",
        "ETFs",
        "El dinero total que gestiona el fondo.",
        "Suma del valor de todo lo que tiene el fondo.",
        "Fondos de más de 1.000 M€ suelen ser más líquidos y con menos riesgo de cierre.",
        "Un fondo grande no es necesariamente mejor: importa qué índice replica y su coste.",
    ),
    Entry(
        "ytd_return",
        "Rentabilidad en el año (YTD)",
        "ETFs",
        "Cuánto ha subido o bajado desde el 1 de enero.",
        "Valor liquidativo hoy / valor el 1 de enero − 1.",
        "Sirve para contextualizar el año en curso.",
        "Periodo muy corto: no dice nada de la calidad del fondo.",
    ),
    Entry(
        "return_3y",
        "Rentabilidad media a 3 años",
        "ETFs",
        "Rentabilidad anual media de los últimos 3 años.",
        "(Valor final / valor inicial)^(1/3) − 1.",
        "Compárala con la del índice que replica: la diferencia es lo que pierdes por costes "
        "(tracking difference).",
        "Rentabilidades pasadas no garantizan las futuras.",
    ),
    Entry(
        "return_5y",
        "Rentabilidad media a 5 años",
        "ETFs",
        "Rentabilidad anual media de los últimos 5 años.",
        "(Valor final / valor inicial)^(1/5) − 1.",
        "Más representativa que la de 1 o 3 años, aunque sigue dependiendo del momento del ciclo.",
        "Rentabilidades pasadas no garantizan las futuras.",
    ),
    # --- Precio, momentum y riesgo -----------------------------------------------------------
    Entry(
        "ret_12m",
        "Rentabilidad a 12 meses",
        "Momentum",
        "Cuánto ha variado el precio en el último año.",
        "Precio hoy / precio hace 12 meses − 1 (precios ajustados por dividendos y splits).",
        "Los estudios académicos encuentran cierto efecto 'momentum': lo que ha subido en "
        "los últimos 6-12 meses tiende a seguir algo mejor que el resto a corto plazo.",
        "El efecto es débil, se invierte a plazos largos y sufre caídas bruscas. Pasado no es "
        "futuro.",
    ),
    Entry(
        "ret_6m",
        "Rentabilidad a 6 meses",
        "Momentum",
        "Cuánto ha variado el precio en los últimos 6 meses.",
        "Precio hoy / precio hace 6 meses − 1.",
        "Igual que la de 12 meses, a más corto plazo.",
        "Más ruidosa que la de 12 meses.",
    ),
    Entry(
        "dist_sma200",
        "Distancia a la media de 200 sesiones",
        "Momentum",
        "Cuánto está el precio por encima o por debajo de su media de los últimos ~10 meses.",
        "Precio / SMA 200 − 1.",
        "Positiva = tendencia de largo plazo alcista según el análisis técnico clásico. Muy "
        "por encima (+30 %) puede indicar una subida muy extendida.",
        "Es una media del pasado: reacciona tarde a los cambios.",
    ),
    Entry(
        "vol_1y",
        "Volatilidad anualizada",
        "Riesgo",
        "Cuánto oscila el precio. Una volatilidad del 25 % significa que, en un año normal, "
        "es habitual que el precio se mueva ±25 % respecto a su tendencia.",
        "Desviación típica de los rendimientos diarios del último año × √252.",
        "Grandes empresas estables: 15-25 %; tecnológicas o cíclicas: 30-50 %; índices "
        "amplios: 12-20 %.",
        "Trata igual subidas y bajadas, y supone que los movimientos extremos son raros "
        "(en bolsa lo son menos de lo que dice la estadística normal).",
    ),
    Entry(
        "mdd_1y",
        "Caída máxima (drawdown)",
        "Riesgo",
        "La peor caída desde un máximo hasta un mínimo posterior. Responde a '¿cuánto habría "
        "llegado a perder si hubiera comprado en el peor momento?'.",
        "min(precio / máximo previo − 1) en el periodo.",
        "Más cerca de 0 = menos sufrimiento. Pregúntate si aguantarías esa caída sin vender: "
        "es la mejor prueba de tu tolerancia real al riesgo.",
        "Con un año de datos, una crisis anterior no aparece. Los índices amplios han caído "
        "más de un 50 % en crisis como 2008.",
    ),
    # --- Indicadores técnicos (no están en el catálogo de métricas) -------------------------
    Entry(
        "sma",
        "Media móvil simple (SMA)",
        "Análisis técnico",
        "El precio medio de las últimas N sesiones. Suaviza el ruido para ver la tendencia.",
        "Suma de los últimos N cierres / N. La de 50 sesiones ≈ 2,5 meses; la de 200 ≈ 10 meses.",
        "Precio por encima de la SMA 200 = tendencia alcista de largo plazo (lectura clásica). "
        "'Cruce dorado': la SMA 50 cruza al alza la SMA 200; 'cruce de la muerte': a la baja.",
        "Va siempre con retraso: cuando confirma una tendencia, buena parte del movimiento ya "
        "ha ocurrido. En mercados laterales da muchas señales falsas.",
    ),
    Entry(
        "rsi",
        "RSI (índice de fuerza relativa)",
        "Análisis técnico",
        "Compara la fuerza de las subidas recientes con la de las bajadas, en una escala de "
        "0 a 100.",
        "RSI = 100 − 100 / (1 + RS), donde RS = media de las subidas / media de las bajadas "
        "de las últimas 14 sesiones (suavizado de Wilder).",
        "Por encima de 70 se suele llamar 'sobrecompra' y por debajo de 30, 'sobreventa'.",
        "En tendencias fuertes puede pasar semanas por encima de 70 mientras el precio sigue "
        "subiendo. Distintas webs usan suavizados distintos y dan valores algo diferentes.",
    ),
    Entry(
        "macd",
        "MACD",
        "Análisis técnico",
        "Mide el impulso comparando una media rápida y una lenta.",
        "MACD = EMA 12 − EMA 26. Señal = EMA 9 del MACD. Histograma = MACD − señal.",
        "MACD por encima de su señal = impulso positivo (lectura clásica); los cruces se "
        "usan como señales.",
        "Basado en medias: llega tarde y genera muchas señales falsas en mercados laterales.",
    ),
    Entry(
        "bollinger",
        "Bandas de Bollinger",
        "Análisis técnico",
        "Un 'canal' alrededor de la media que se ensancha cuando el precio oscila más.",
        "Media de 20 sesiones ± 2 desviaciones típicas.",
        "Tocar la banda superior indica un movimiento fuerte al alza; bandas muy estrechas "
        "indican calma, que a menudo precede a movimientos amplios (sin indicar hacia dónde).",
        "Salir de las bandas no significa que el precio vaya a volver: en tendencias fuertes "
        "puede 'caminar' por la banda.",
    ),
    Entry(
        "support_resistance",
        "Soportes y resistencias",
        "Análisis técnico",
        "Zonas de precio donde la cotización ha girado varias veces: un soporte frenó caídas y "
        "una resistencia frenó subidas.",
        "En esta app: máximos y mínimos locales del último año, agrupados si están a menos "
        "de un 2 % entre sí. Más 'toques' = nivel más relevante.",
        "Muchos inversores vigilan estos niveles, así que a veces funcionan por profecía "
        "autocumplida.",
        "Son zonas aproximadas, no precios exactos, y se rompen con frecuencia.",
    ),
    # --- Herramientas de la app --------------------------------------------------------------
    Entry(
        "score",
        "Score de Radar Bolsa (0-100)",
        "Herramientas de la app",
        "Un resumen de cómo se comparan las métricas de una empresa con las de sus "
        "comparables, en cinco bloques: valoración, salud, crecimiento, momentum y riesgo.",
        "Cada métrica → percentil frente al sector (o frente a todo el universo en momentum y "
        "riesgo). Bloque = media de percentiles × 100. Total = media ponderada de los bloques.",
        "50 = en la mediana de sus comparables. Más de 70: métricas claramente mejores; menos "
        "de 30: claramente peores.",
        "Es relativo a un universo de ~140 grandes empresas, usa una sola fuente de datos y "
        "pesos subjetivos. No es una recomendación de compra ni de venta.",
    ),
    Entry(
        "sentiment",
        "Sentimiento de noticias",
        "Herramientas de la app",
        "Una medida aproximada de si los titulares recientes son positivos o negativos.",
        "Se cuentan palabras de listas positivas y negativas en cada titular; 'no' o 'sin' "
        "justo antes invierten el signo. Tono = (positivas − negativas) / total.",
        "Sirve para detectar rápidamente si hay ruido fuerte (resultados, multas, "
        "operaciones corporativas) alrededor de una empresa.",
        "No entiende contexto ni ironía. Cuando una noticia sale en prensa, el mercado ya "
        "suele haberla descontado en el precio.",
    ),
]


def by_key() -> dict[str, Entry]:
    return {e.key: e for e in ENTRIES}


def categories() -> list[str]:
    return list(dict.fromkeys(e.category for e in ENTRIES))
