# Análisis diario de mercado

Script que descarga datos de un conjunto de tickers (acciones y ETFs) vía `yfinance`,
calcula señales técnicas simples (SMA20/SMA50, RSI) y envía un resumen por correo.

## Setup

1. En Gmail, genera una **contraseña de aplicación**:
   https://myaccount.google.com/apppasswords
   (requiere verificación en 2 pasos activada en la cuenta)

2. En este repo: `Settings → Secrets and variables → Actions → New repository secret`,
   agrega:
   - `GMAIL_USER` — tu correo de Gmail
   - `GMAIL_PASS` — la contraseña de aplicación generada
   - `DESTINATARIO` — correo al que quieres recibir el análisis

3. Si aún no configuras los secrets, el workflow corre igual y genera `preview.html`
   como artifact descargable (sin enviar correo) — útil para la primera prueba.

4. Para correrlo manualmente: pestaña **Actions** → "Análisis diario de mercado" →
   "Run workflow".

5. Una vez configurados los secrets, corre automáticamente de lunes a viernes a las
   7:00 AM (hora Centro de México) y además envía el correo.

## Modificar la lista de tickers

Edita la lista `TICKERS` en `analisis.py`.
