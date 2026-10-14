"""Guías «Cómo invertir» (contenido en Markdown, orientado a un particular en España).

Información general y educativa, no asesoramiento. Revisado: octubre de 2026. Las comisiones,
los productos y la fiscalidad cambian: comprueba siempre las tarifas del bróker y la AEAT.
No se recomienda ningún bróker concreto: se explican los criterios para compararlos.
"""

from dataclasses import dataclass

from radar.education.concepts import TAX_ES


@dataclass(frozen=True)
class Guide:
    key: str
    title: str
    summary: str
    body: str  # Markdown


BROKER = """
Un **bróker** es la empresa a través de la cual compras y vendes. Radar Bolsa no se conecta
a ninguno: te dice qué mirar, y la compra la haces tú en el tuyo.

#### Qué comparar
- **Regulación y protección**: que esté autorizado por la **CNMV** (o por un supervisor de la
  UE con pasaporte europeo) y que figure en su registro. Tus valores están separados del
  dinero del bróker; el **Fondo de Garantía de Inversiones** cubre hasta 100.000 € por
  titular y entidad si la entidad quiebra (no cubre pérdidas de mercado).
- **Comisiones**: de compra y venta (fija, porcentual o con mínimo), de **custodia** y de
  **cambio de divisa** si compras fuera del euro. Con importes pequeños, un mínimo de 9 € por
  operación es un 9 % de una compra de 100 €.
- **Mercados y productos**: que ofrezca la bolsa donde cotiza lo que quieres (Bolsa de
  Madrid, Xetra, Euronext, EE. UU.) y los **ETFs UCITS** (los accesibles al pequeño inversor
  en la UE; los ETFs de EE. UU. no se pueden comprar por normativa PRIIPs/KID).
- **Fiscalidad**: un bróker **español** (o con convenio) retiene y te da los datos fiscales.
  Con uno **extranjero** debes calcular y declarar tú, y quizá presentar el modelo 720.
- **Inversión periódica**: si puedes programar compras mensuales automáticas y si admite
  **fracciones** de ETF, para aportar importes pequeños sin comisión desproporcionada.
- **Servicio**: atención en español, app, y facilidad para sacar el dinero.

#### Antes de abrir cuenta
1. Lee la **tarifa de comisiones** completa (la letra pequeña: custodia, inactividad, divisa).
2. Haz un cálculo con tu caso: ¿cuánto pagarías al año con tus aportaciones?
3. Te harán un **test de conveniencia/idoneidad** (MiFID): responde con sinceridad.
4. Empieza con poco dinero para familiarizarte con la plataforma.
"""

ORDERS = """
Una **orden** es la instrucción que das al bróker. Elegir bien el tipo evita sustos.

| Orden | Qué hace | Cuándo usarla | Riesgo |
|---|---|---|---|
| **A mercado** | Compra o vende ya, al mejor precio disponible | Valores muy líquidos (grandes empresas, ETFs grandes) en horario de mercado | En valores poco líquidos o en la apertura puedes pagar un precio peor del esperado |
| **Limitada** | Solo se ejecuta al precio que fijas o mejor | **La opción más segura para empezar**: tú decides el máximo que pagas | Puede no ejecutarse nunca si el precio no llega |
| **Stop** (de pérdidas) | Se activa como orden a mercado cuando el precio toca un nivel | Limitar una pérdida: «si baja a 8 €, vende» | En un hueco o una caída brusca se ejecuta bastante por debajo de tu nivel |
| **Stop-limitada** | Al tocar el nivel, lanza una orden limitada | Más control del precio que la stop | Si el precio salta tu límite, no se ejecuta y sigues dentro |

#### Consejos prácticos
- **Usa órdenes limitadas** con un precio cercano al actual (el rango de entrada de la app
  te da una referencia). Evita las órdenes a mercado en valores pequeños.
- **Horario**: la Bolsa de Madrid abre de 9:00 a 17:30 (hora de Madrid); la subasta de
  apertura y la de cierre tienen más volatilidad. EE. UU. abre a las 15:30 (hora de Madrid).
- **Validez**: una orden puede valer solo para hoy o hasta que la canceles; mira cuál has
  marcado para no encontrarte una compra antigua ejecutada semanas después.
- **Divisa**: comprar en dólares añade el cambio de divisa (coste y riesgo de tipo de cambio).
- **Comprueba el resumen** antes de confirmar: ticker correcto, cantidad, precio y bolsa.
"""  # noqa: E501 (tabla en Markdown)

PERIODIC = """
**Aportar una cantidad fija cada mes** (en inglés, *dollar-cost averaging*) te evita decidir
«cuándo es buen momento»: compras más participaciones cuando el precio baja y menos cuando
sube.

#### Por qué funciona para la mayoría
- **Quita las emociones**: automatizas la decisión y no esperas al «momento perfecto».
- **Se adapta a tu economía**: se invierte lo que ahorras cada mes, no un gran capital.
- **Aprovecha el tiempo**: más meses invertidos, más efecto del interés compuesto.

#### Sus límites (honestidad)
- **No garantiza ganar ni evita pérdidas**: si el mercado cae durante años, pierdes igual.
- Si ya tienes un capital grande, estudios históricos muestran que invertirlo todo de una
  vez ha rendido de media algo más que repartirlo, porque el mercado sube más veces de las
  que baja; repartir reduce el arrepentimiento, no el riesgo de largo plazo.
- Con comisiones fijas por operación, aportaciones muy pequeñas salen caras: elige
  periodicidad (mensual o trimestral) y un bróker acordes.

#### Cómo hacerlo
1. Decide una cantidad que puedas mantener incluso en meses malos.
2. Elige el día (p. ej. el día después de cobrar) y automatiza la compra si tu bróker lo permite.
3. Mantén el reparto de tu cartera (ETF base, acciones, parte segura) y **rebalancea** solo
   una o dos veces al año, no cada semana.
4. Prueba la calculadora de abajo para ver el efecto del tiempo y de las comisiones.
"""

EMERGENCY = """
Antes de invertir, necesitas un colchón. **Invertir dinero que puedes necesitar pronto
obliga a vender en el peor momento.**

#### Cuánto
- **3 a 6 meses de gastos fijos** (alquiler o hipoteca, comida, suministros, seguros, deudas).
  Más cerca de 6 meses (o más) si tus ingresos son variables, eres autónomo o tienes
  personas a cargo.
- Ejemplo: gastos de 1.500 €/mes → entre 4.500 € y 9.000 €.

#### Dónde
- **Cuenta remunerada o depósito a corto plazo**, o un fondo monetario: poco riesgo y acceso
  rápido. No lo pongas en bolsa, ni en acciones, ni en nada que pueda caer un 30 % justo
  cuando lo necesites.
- Separado de tu cuenta del día a día, para no gastarlo sin querer.

#### Orden recomendado
1. Paga primero las deudas caras (tarjetas, préstamos al consumo: intereses muy superiores
   a lo que razonablemente rinde la bolsa).
2. Forma el fondo de emergencia.
3. Solo entonces, invierte el dinero que no necesitarás durante años: **horizonte mínimo
   orientativo de 5 años** para la parte en bolsa.

El test de perfil de la app ya te pregunta si tienes este colchón; si respondes que no, tu
perfil sale más prudente.
"""

GUIDES: list[Guide] = [
    Guide("broker", "Elegir bróker en España", "Qué comparar antes de abrir cuenta.", BROKER),
    Guide("ordenes", "Tipos de órdenes", "Mercado, limitada, stop y cuándo usar cada una.", ORDERS),
    Guide(
        "aportaciones",
        "Aportaciones periódicas",
        "Invertir una cantidad fija cada mes, con sus ventajas y límites.",
        PERIODIC,
    ),
    Guide(
        "emergencia",
        "Fondo de emergencia",
        "El colchón que necesitas antes de invertir.",
        EMERGENCY,
    ),
    Guide(
        "fiscalidad",
        "Fiscalidad en España",
        "Cómo tributan dividendos y ventas (información general).",
        TAX_ES,
    ),
]
BY_KEY = {g.key: g for g in GUIDES}
