"""Conceptos básicos de inversión y fiscalidad general en España (contenido en Markdown).

Información general y educativa. La fiscalidad cambia: verificar siempre en la AEAT
(sede.agenciatributaria.gob.es) o con un asesor. Revisado: octubre de 2026.
"""

from dataclasses import dataclass

CONCEPTS: dict[str, str] = {
    "Diversificación": """
**No poner todos los huevos en la misma cesta.** Si tienes una sola empresa y le va mal, tu
inversión sufre entera; si tienes 30 de sectores y países distintos, el problema de una pesa
poco en el total.

- Reduce el riesgo **específico** (el de cada empresa: un fraude, un mal producto, una
  multa). No elimina el riesgo de **mercado**: en una crisis general casi todo cae a la vez.
- Diversificar no es solo tener muchas posiciones: 10 bancos españoles son, en la práctica,
  casi una sola apuesta. Importa repartir entre **sectores, países y tipos de activo**.
- En la cartera simulada verás el **número efectivo de posiciones** (1 / Σ peso²): mide
  cuántas posiciones "de verdad" tienes según cómo repartes el dinero.
- Un ETF de un índice mundial (p. ej. MSCI World) te da más de 1.000 empresas en una compra.
""",
    "ETFs frente a acciones individuales": """
| | ETF indexado | Acciones individuales |
|---|---|---|
| Qué compras | Una cesta que replica un índice | Una parte de una empresa concreta |
| Diversificación | Alta desde la primera compra | Necesitas muchas para diversificar |
| Coste | TER anual (0,05-0,25 %) | Sin coste anual, pero comisión por compra |
| Trabajo | Muy poco | Analizar y seguir cada empresa |
| Resultado esperado | El del mercado, menos costes | Puede ser mejor o peor que el mercado |

**El dato incómodo:** la mayoría de los fondos de gestión activa no superan a su índice
a 10-15 años después de costes (los informes SPIVA de S&P lo miden cada año). Elegir
acciones puede ser muy formativo, pero conviene medir si aporta algo: para eso la cartera
simulada te compara con un índice.

Detalles prácticos: los ETFs de **acumulación** reinvierten los dividendos (no pagan
impuestos hasta que vendes) y los de **distribución** los pagan (tributan al cobrarlos).
""",
    "Interés compuesto": """
Ganar rentabilidad **sobre la rentabilidad anterior**. Con un 7 % anual, 10.000 € se
convierten en 10.700 € el primer año, pero el segundo año el 7 % se aplica sobre 10.700 €, y
así sucesivamente: en 30 años son ~76.000 €, aunque solo pusiste 10.000.

- **El tiempo es el ingrediente principal**: empezar 10 años antes suele importar más que
  aportar algo más cada mes.
- **Regla del 72**: 72 / rentabilidad anual (%) ≈ años para duplicar. Al 6 %, unos 12 años.
- **Funciona igual con los costes**: una comisión del 1,5 % anual frente a una del 0,2 % se
  come una parte enorme del resultado a 30 años. Pruébalo en la calculadora.
- **Inflación**: lo que importa es la rentabilidad real (descontando la inflación).
""",
    "Horizonte temporal": """
**¿Cuándo vas a necesitar el dinero?** Es la pregunta más importante antes de invertir.

- La bolsa puede caer un 30-50 % en una crisis y tardar años en recuperarse. El dinero que
  necesites en los próximos 2-3 años no debería depender de ella.
- A plazos largos (15-20 años o más), históricamente, la bolsa mundial ha dado rentabilidades
  positivas en la gran mayoría de los periodos, pero no hay garantía.
- Antes de invertir: un **fondo de emergencia** (3-6 meses de gastos) en algo líquido y sin
  riesgo, y sin deudas caras (tarjetas, préstamos al consumo).
- Cuanto más largo el horizonte, más volatilidad puedes permitirte... **si de verdad la
  aguantas sin vender en el peor momento**.
""",
    "Riesgo y rentabilidad": """
No existe rentabilidad alta sin riesgo. Si alguien promete lo contrario, desconfía.

- **Volatilidad**: cuánto oscila el precio. **Caída máxima (drawdown)**: cuánto llegó a caer
  desde un máximo. La segunda se entiende mejor: "¿soportarías ver tu inversión un 35 % abajo?"
- Las acciones han rendido más que la renta fija a largo plazo **a cambio** de caídas más
  fuertes.
- El peor riesgo no siempre es el del mercado: es vender por pánico en una caída, o
  concentrarse en una sola empresa que te gusta.
""",
    "Sesgos del inversor": """
Errores mentales habituales (y por qué esta app intenta no fomentarlos):

- **Exceso de confianza**: creer que sabemos más que el mercado. El score y los indicadores
  son ayudas, no certezas.
- **Sesgo de confirmación**: buscar solo los datos que apoyan lo que ya pensamos. Por eso la
  app muestra argumentos a favor **y en contra**.
- **Aversión a las pérdidas**: duele más perder 100 € que alegra ganarlos; lleva a vender lo
  que sube y mantener lo que baja.
- **Efecto rebaño / FOMO**: comprar lo que está de moda tras subir mucho.
- **Sesgo de resultado**: juzgar una decisión por el resultado y no por el razonamiento.
  Apunta en cada operación simulada **por qué** la haces y revísalo meses después.
""",
}


TAX_ES = """
> ⚠️ **Información general, no asesoramiento fiscal.** Resumen orientativo para residentes
> fiscales en España (IRPF, territorio común), revisado en octubre de 2026. La normativa
> cambia y hay particularidades (País Vasco y Navarra tienen régimen propio). Comprueba siempre
> en la **[sede de la Agencia Tributaria](https://sede.agenciatributaria.gob.es)** o con un asesor.

#### ¿Qué tributa y cuándo?
- **Dividendos** e intereses: son *rendimientos del capital mobiliario*. Tributan el año en
  que los cobras. El bróker español suele retener ya un **19 %** a cuenta.
- **Ventas** de acciones o ETFs: si vendes por más de lo que compraste, tienes una
  *ganancia patrimonial*; si vendes por menos, una *pérdida*. Solo tributa al **vender**:
  mientras no vendas, la ganancia "latente" no paga impuestos.
- Las comisiones de compra y venta forman parte del coste y del importe de venta.

#### ¿A qué tipo?
Ambos van a la **base del ahorro**, que tributa por tramos (desde 2025):

| Base del ahorro | Tipo |
|---|---|
| Hasta 6.000 € | 19 % |
| De 6.000 a 50.000 € | 21 % |
| De 50.000 a 200.000 € | 23 % |
| De 200.000 a 300.000 € | 27 % |
| Más de 300.000 € | 30 % |

Es progresivo **por tramos**: con 10.000 € de ganancia, los primeros 6.000 tributan al 19 %
y los 4.000 restantes al 21 % (no todo al 21 %). Puedes probarlo en la calculadora de abajo.

#### Reglas que conviene conocer
- **FIFO**: si compraste las mismas acciones en varias fechas, al vender se considera que
  vendes primero las más antiguas. La cartera simulada calcula así las ganancias.
- **Compensación de pérdidas**: las pérdidas por ventas se compensan con ganancias por
  ventas del mismo año. Si sobra pérdida, puede compensar hasta el **25 %** del saldo
  positivo de dividendos e intereses, y lo que quede, en los **4 años siguientes**.
- **Regla de los dos meses**: si vendes con pérdidas y recompras los mismos valores en los
  **2 meses anteriores o posteriores** (1 año si no cotizan en mercados regulados), no
  puedes aplicar esa pérdida ahora: se aplaza hasta que vendas los valores recomprados.
- **Traspasos**: entre **fondos de inversión** se puede cambiar de fondo sin tributar
  (se difiere hasta el reembolso). Los **ETFs**, en general, **no** tienen esta ventaja:
  vender un ETF para comprar otro es una venta que tributa.

#### Inversiones en el extranjero
- **Dividendos extranjeros**: el país de origen suele retener (EE. UU. un 15 % si has
  firmado el formulario W-8BEN; otros países, más). En España puedes deducir la **doble
  imposición internacional**, con límites: normalmente, hasta el tipo del convenio. Lo
  retenido de más solo se recupera reclamándolo al país de origen.
- **Bróker extranjero**: si tienes valores depositados fuera de España por más de
  **50.000 €**, puede que debas presentar el **modelo 720** (declaración informativa).
  Además, con un bróker extranjero nadie te practica retenciones ni te prepara los datos
  fiscales: te toca calcularlo a ti.

#### Ejemplo
Compras 100 acciones a 10 € (comisión 5 €) y las vendes a 15 € (comisión 5 €).
Ganancia = (1.500 − 5) − (1.000 + 5) = **490 €**, que van a la base del ahorro (19 % → 93,10 €).
"""


@dataclass(frozen=True)
class Question:
    text: str
    options: list[tuple[str, int]]  # (respuesta, puntos 1-3)


RISK_QUESTIONS: list[Question] = [
    Question("¿Cuándo crees que necesitarás este dinero?",
             [("En menos de 3 años", 1), ("Entre 3 y 10 años", 2), ("En más de 10 años", 3)]),
    Question("Tu inversión cae un 30 % en pocos meses. ¿Qué harías?",
             [("Vender para no perder más", 1), ("Esperar sin hacer nada", 2),
              ("Mantener e incluso aportar más", 3)]),
    Question("¿Qué te preocupa más?",
             [("No perder dinero", 1), ("Un equilibrio entre ganar y no perder", 2),
              ("Ganar lo máximo a largo plazo aunque haya sustos", 3)]),
    Question("¿Tienes un fondo de emergencia (3-6 meses de gastos) aparte?",
             [("No", 1), ("Parcialmente", 2), ("Sí", 3)]),
    Question("¿Cuánta experiencia tienes invirtiendo?",
             [("Ninguna", 1), ("Algo (fondos, depósitos...)", 2),
              ("Bastante (acciones, ETFs, varios años)", 3)]),
]  # fmt: skip


def risk_profile(points: list[int]) -> tuple[str, str]:
    """Perfil orientativo a partir de los puntos (5–15). No sustituye al test de idoneidad
    que tu banco o bróker debe hacerte por normativa (MiFID)."""
    total = sum(points)
    if total <= 8:
        return (
            "Conservador",
            "Priorizas no perder y/o necesitas el dinero pronto. La renta variable debería "
            "tener un peso pequeño, y la volatilidad de acciones individuales probablemente "
            "te incomodará.",
        )
    if total <= 12:
        return (
            "Moderado",
            "Aceptas oscilaciones a cambio de más rentabilidad esperada. Una mezcla de renta "
            "variable diversificada y renta fija suele encajar con este perfil.",
        )
    return (
        "Dinámico",
        "Tienes horizonte largo, colchón y tolerancia a las caídas. Puedes asumir más renta "
        "variable, pero recuerda que tolerar un 30 % de caída en un cuestionario es más fácil "
        "que vivirlo.",
    )
