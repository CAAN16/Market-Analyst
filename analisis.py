import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

import yfinance as yf
import pandas as pd

TICKERS = [
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL",
    "WALMEX.MX", "GFNORTEO.MX", "AMXL.MX",
    "SPY", "QQQ", "VOO",
]

def calcular_sma(serie, periodo):
    return serie.rolling(window=periodo).mean()


def calcular_rsi(serie, periodo=14):
    delta = serie.diff()
    ganancia = delta.clip(lower=0)
    perdida = -delta.clip(upper=0)
    avg_ganancia = ganancia.rolling(window=periodo).mean()
    avg_perdida = perdida.rolling(window=periodo).mean()
    rs = avg_ganancia / avg_perdida
    return 100 - (100 / (1 + rs))

def analizar_ticker(ticker):
    try:
        data = yf.download(ticker, period="6mo", interval="1d", progress=False)
        if data.empty or len(data) < 50:
            print(f"[{ticker}] datos insuficientes")
            return None

        close = data["Close"]
        if isinstance(close, pd.DataFrame):
            close = close.iloc[:, 0]

        sma20 = calcular_sma(close, 20)
        sma50 = calcular_sma(close, 50)
        rsi = calcular_rsi(close, 14)

        precio_actual = float(close.iloc[-1])
        sma20_actual = float(sma20.iloc[-1])
        sma50_actual = float(sma50.iloc[-1])
        rsi_actual = float(rsi.iloc[-1])

        var_1d = (close.iloc[-1] / close.iloc[-2] - 1) * 100
        var_7d = (close.iloc[-1] / close.iloc[-6] - 1) * 100 if len(close) > 6 else None
        var_30d = (close.iloc[-1] / close.iloc[-21] - 1) * 100 if len(close) > 21 else None

        tendencia_alcista = sma20_actual > sma50_actual
        rsi_sobrecompra = rsi_actual > 70
        rsi_sobreventa = rsi_actual < 30

        if tendencia_alcista and not rsi_sobrecompra:
            señal = "Favorable"
        elif rsi_sobreventa:
            señal = "Posible rebote (sobreventa)"
        elif rsi_sobrecompra:
            señal = "Precaución (sobrecompra)"
        else:
            señal = "Neutral"

        return {
            "ticker": ticker,
            "precio": round(precio_actual, 2),
            "var_1d": round(float(var_1d), 2),
            "var_7d": round(float(var_7d), 2) if var_7d is not None else None,
            "var_30d": round(float(var_30d), 2) if var_30d is not None else None,
            "rsi": round(rsi_actual, 1),
            "tendencia": "Alcista" if tendencia_alcista else "Bajista",
            "señal": señal,
        }
    except Exception as e:
        print(f"Error con {ticker}: {e}")
        return None


def generar_html(resultados):
    fecha = datetime.now().strftime("%d/%m/%Y")
    filas = ""
    for r in resultados:
        if r is None:
            continue
        filas += f"""
        <tr>
            <td>{r['ticker']}</td>
            <td>${r['precio']}</td>
            <td>{r['var_1d']}%</td>
            <td>{r['var_7d']}%</td>
            <td>{r['var_30d']}%</td>
            <td>{r['rsi']}</td>
            <td>{r['tendencia']}</td>
            <td>{r['señal']}</td>
        </tr>
        """

    return f"""
    <html>
    <body style="font-family: Arial, sans-serif;">
        <h2>Análisis de mercado — {fecha}</h2>
        <table border="1" cellpadding="6" cellspacing="0" style="border-collapse: collapse;">
            <tr style="background-color:#eee;">
                <th>Ticker</th><th>Precio</th><th>1D</th><th>7D</th><th>30D</th>
                <th>RSI</th><th>Tendencia</th><th>Señal</th>
            </tr>
            {filas}
        </table>
        <p style="font-size:12px;color:#888;">
            Generado automáticamente. No constituye asesoría financiera.
        </p>
    </body>
    </html>
    """


def enviar_correo(asunto, cuerpo_html):
    remitente = os.environ["GMAIL_USER"]
    password = os.environ["GMAIL_PASS"]
    destinatario = os.environ["DESTINATARIO"]

    msg = MIMEMultipart("alternative")
    msg["Subject"] = asunto
    msg["From"] = remitente
    msg["To"] = destinatario
    msg.attach(MIMEText(cuerpo_html, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(remitente, password)
        server.sendmail(remitente, destinatario, msg.as_string())


if __name__ == "__main__":
    resultados = [analizar_ticker(t) for t in TICKERS]
    resultados = [r for r in resultados if r is not None]

    print("\n--- RESULTADOS ---")
    for r in resultados:
        print(r)

    html = generar_html(resultados)
    with open("preview.html", "w", encoding="utf-8") as f:
        f.write(html)
    print(f"\n{len(resultados)}/{len(TICKERS)} tickers procesados correctamente.")

    # Si las credenciales de correo están presentes (secrets configurados), envía.
    # Si no, solo genera preview.html para revisar el resultado (modo prueba).
    if all(k in os.environ for k in ("GMAIL_USER", "GMAIL_PASS", "DESTINATARIO")):
        fecha = datetime.now().strftime("%d/%m/%Y")
        enviar_correo(f"Análisis de mercado — {fecha}", html)
        print("Correo enviado correctamente.")
    else:
        print("Variables GMAIL_USER/GMAIL_PASS/DESTINATARIO no configuradas — solo se generó preview.html (modo prueba).")
