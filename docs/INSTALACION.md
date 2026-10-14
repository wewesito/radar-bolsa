# Instalar Radar Bolsa en el Mac

Guía paso a paso para instalar la app de escritorio, crear su acceso directo y, si hace
falta, volver a generarla desde el código.

> Radar Bolsa genera recomendaciones con un modelo propio a partir de datos públicos. No
> garantizan rentabilidad y no sustituyen a un asesor financiero.

## Requisitos

- Un Mac con chip Apple (M1 o posterior) y macOS 12 Monterey o más reciente.
- Conexión a internet: los datos se descargan de Yahoo Finance.

## 1. Instalar la app

1. Abre el instalador `Radar Bolsa_0.2.0_aarch64.dmg`. Está en
   `desktop/src-tauri/target/release/bundle/dmg/` dentro del proyecto.
2. En la ventana que aparece, arrastra el icono de **Radar Bolsa** a la carpeta
   **Aplicaciones**.
3. Expulsa el disco «Radar Bolsa» desde la barra lateral del Finder.

### Si macOS no la deja abrir

La app no está firmada con un certificado de Apple Developer (cuesta 99 $ al año). Si la
generaste en este mismo Mac, se abre sin avisos. Si la copiaste de otro ordenador, macOS
puede decir que «no se puede abrir porque Apple no puede comprobar que no contiene
software malicioso». En ese caso:

1. Pulsa **OK** en el aviso.
2. Abre **Ajustes del Sistema → Privacidad y seguridad**.
3. Baja hasta la sección **Seguridad**. Verás un mensaje sobre Radar Bolsa: pulsa
   **Abrir igualmente** y confirma con tu contraseña o Touch ID.

Solo hay que hacerlo una vez.

## 2. Crear el acceso directo

**En el Dock (recomendado):**

1. Abre la app desde **Aplicaciones** (o con Spotlight: ⌘ + espacio y escribe «Radar»).
2. Con la app abierta, haz clic derecho en su icono del Dock → **Opciones → Mantener en
   el Dock**.

**En el Escritorio:**

1. Abre una ventana del Finder y entra en **Aplicaciones**.
2. Mantén pulsadas las teclas **⌥ Opción + ⌘ Comando** y arrastra **Radar Bolsa** al
   Escritorio. Se crea un alias (el icono lleva una flecha pequeña).
   - Otra forma: clic derecho sobre la app → **Crear alias** y arrastra el alias al
     Escritorio.

También aparece sola en el **Launchpad**.

## 3. Primer uso

1. **Primer arranque:** la primera vez que abres la app, el motor de datos tarda unos
   10–15 segundos en arrancar, porque macOS revisa sus archivos. Las siguientes veces
   tarda menos de un segundo.
2. **Test de perfil:** 5 preguntas (horizonte, tolerancia al riesgo, cantidad, objetivo y
   experiencia). Puedes repetirlo cuando quieras desde **Mi perfil inversor**.
3. **Descarga de datos:** mientras haces el test, la app descarga los datos de unos 225
   valores. Tarda alrededor de un minuto. Después se guardan en el Mac.
4. **Actualizar datos:** pulsa la fecha de los datos en la barra superior, o ve a
   **Ajustes → Actualizar datos ahora**. Con hacerlo una vez por semana basta: los
   fundamentales cambian cada trimestre. Las cotizaciones del día se refrescan solas.

## 4. API keys (opcional)

En **Ajustes y API keys** puedes guardar la clave gratuita de
[Finnhub](https://finnhub.io), que añade noticias de empresas de EE. UU.

La clave se guarda en el **Llavero de macOS**, nunca en el código ni en un archivo. Para
verla o borrarla: app **Acceso a Llaveros** → busca «Radar Bolsa».

## 5. Dónde se guardan tus datos y cómo desinstalar

- Perfil, ajustes y caché: `~/Library/Application Support/Radar Bolsa/` (en el Finder,
  menú **Ir → Ir a la carpeta…** y pega esa ruta).
- Para desinstalar:
  1. Arrastra la app de **Aplicaciones** a la Papelera.
  2. Borra la carpeta `~/Library/Application Support/Radar Bolsa/`.
  3. Si guardaste una clave, bórrala de **Acceso a Llaveros**.

## 6. Volver a generar la app desde el código

Hace falta una vez:

- **Herramientas de línea de comandos de Xcode:** `xcode-select --install`
- **Python 3.11 o posterior** (python.org).
- **Node.js 20 o posterior y Rust.** En este Mac ya están instalados en tu carpeta de
  usuario (`~/.local/node` y `~/.cargo`), sin tocar el sistema. Para usarlos en la
  terminal:

  ```bash
  export PATH="$HOME/.local/node/bin:$HOME/.cargo/bin:$PATH"
  ```

  En otro Mac, instala Node desde nodejs.org y Rust desde rustup.rs.

Después, desde la carpeta del proyecto:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
bash desktop/scripts/build_app.sh
```

El script empaqueta el motor en Python con PyInstaller, compila la ventana con Tauri y
deja el resultado en:

- `desktop/src-tauri/target/release/bundle/dmg/Radar Bolsa_0.2.0_aarch64.dmg`, el
  instalador.
- `desktop/src-tauri/target/release/bundle/macos/Radar Bolsa.app`, la app.

Si ya tenías la app instalada, sustitúyela: arrastra la nueva a **Aplicaciones** y elige
**Reemplazar**. Tu perfil y tus datos no se pierden.

## 7. Problemas frecuentes

| Síntoma | Qué hacer |
|---|---|
| Se queda en «Arrancando el motor de datos…» más de un minuto | Cierra la app (⌘Q) y vuelve a abrirla. Si sigue igual, vuelve a generarla (apartado 6). |
| «Yahoo está limitando las peticiones» | Espera uno o dos minutos. La app sigue mostrando la última copia guardada, marcada como «copia antigua». |
| Un valor aparece como «Evitar» con «No cotiza desde…» | Ha dejado de cotizar (por ejemplo, tras una OPA). Sus datos ya no son fiables. |
| Faltan datos de alguna empresa pequeña | Yahoo no los publica. La app lo indica con «n/d» en lugar de inventarlos. |
