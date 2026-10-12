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


# --- Indicadores ---

def calcular_sma(serie, periodo):
    return serie.rolling(window=periodo).mean()


def calcular_ema(serie, periodo):
    return serie.ewm(span=periodo, adjust=False).mean()


def calcular_rsi(serie, periodo=14):
    delta = serie.diff()
    ganancia = delta.clip(lower=0)
    perdida = -delta.clip(upper=0)
    avg_ganancia = ganancia.rolling(window=periodo).mean()
    avg_perdida = perdida.rolling(window=periodo).mean()
    rs = avg_ganancia / avg_perdida
    return 100 - (100 / (1 + rs))


def calcular_macd(serie, rapida=12, lenta=26, señal=9):
    ema_rapida = calcular_ema(serie, rapida)
    ema_lenta = calcular_ema(serie, lenta)
    macd_line = ema_rapida - ema_lenta
    señal_line = calcular_ema(macd_line, señal)
    histograma = macd_line - señal_line
    return macd_line, señal_line, histograma


def calcular_atr(high, low, close, periodo=14):
    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=periodo).mean()


# --- Análisis por ticker ---

def analizar_ticker(ticker):
    try:
        data = yf.download(ticker, period="1y", interval="1d", progress=False)
        if data.empty or len(data) < 60:
            print(f"[{ticker}] datos insuficientes")
            return None

        close = data["Close"]
        high = data["High"]
        low = data["Low"]
        volume = data["Volume"]

        if isinstance(close, pd.DataFrame):
            close = close.iloc[:, 0]
        if isinstance(high, pd.DataFrame):
            high = high.iloc[:, 0]
        if isinstance(low, pd.DataFrame):
            low = low.iloc[:, 0]
        if isinstance(volume, pd.DataFrame):
            volume = volume.iloc[:, 0]

        sma20 = calcular_sma(close, 20)
        sma50 = calcular_sma(close, 50)
        rsi = calcular_rsi(close, 14)
        macd_line, macd_señal, macd_hist = calcular_macd(close)
        atr = calcular_atr(high, low, close, 14)

        precio_actual = float(close.iloc[-1])
        sma20_actual = float(sma20.iloc[-1])
        sma50_actual = float(sma50.iloc[-1])
        rsi_actual = float(rsi.iloc[-1])
        macd_hist_actual = float(macd_hist.iloc[-1])
        macd_hist_prev = float(macd_hist.iloc[-2])
        atr_actual = float(atr.iloc[-1])

        var_1d = (close.iloc[-1] / close.iloc[-2] - 1) * 100
        var_7d = (close.iloc[-1] / close.iloc[-6] - 1) * 100 if len(close) > 6 else None
        var_30d = (close.iloc[-1] / close.iloc[-21] - 1) * 100 if len(close) > 21 else None

        # Volumen vs. promedio de 20 días
        vol_actual = float(volume.iloc[-1])
        vol_promedio20 = float(volume.rolling(window=20).mean().iloc[-1])
        vol_ratio = (vol_actual / vol_promedio20) if vol_promedio20 > 0 else None

        # Volatilidad relativa (ATR como % del precio)
        volatilidad_pct = (atr_actual / precio_actual) * 100

        # Máximo / mínimo de 52 semanas y distancia al máximo
        max_52s = float(close.max())
        min_52s = float(close.min())
        dist_max_52s = ((precio_actual / max_52s) - 1) * 100  # negativo = % debajo del máximo

        # Señales
        tendencia_alcista = sma20_actual > sma50_actual
        rsi_sobrecompra = rsi_actual > 70
        rsi_sobreventa = rsi_actual < 30
        macd_cruce_alcista = macd_hist_prev < 0 and macd_hist_actual > 0
        macd_cruce_bajista = macd_hist_prev > 0 and macd_hist_actual < 0
        volumen_alto = vol_ratio is not None and vol_ratio > 1.5

        if tendencia_alcista and not rsi_sobrecompra and macd_hist_actual > 0:
            señal = "Favorable"
            color = "#1a7f37"
        elif rsi_sobreventa or macd_cruce_alcista:
            señal = "Posible rebote"
            color = "#9a6700"
        elif rsi_sobrecompra or macd_cruce_bajista:
            señal = "Precaución"
            color = "#cf222e"
        else:
            señal = "Neutral"
            color = "#57606a"

        return {
            "ticker": ticker,
            "precio": round(precio_actual, 2),
            "var_1d": round(float(var_1d), 2),
            "var_7d": round(float(var_7d), 2) if var_7d is not None else None,
            "var_30d": round(float(var_30d), 2) if var_30d is not None else None,
            "rsi": round(rsi_actual, 1),
            "macd_hist": round(macd_hist_actual, 3),
            "tendencia": "Alcista" if tendencia_alcista else "Bajista",
            "volumen_ratio": round(vol_ratio, 2) if vol_ratio is not None else None,
            "volumen_alto": volumen_alto,
            "volatilidad_pct": round(volatilidad_pct, 2),
            "dist_max_52s": round(dist_max_52s, 2),
            "max_52s": round(max_52s, 2),
            "min_52s": round(min_52s, 2),
            "señal": señal,
            "color": color,
        }
    except Exception as e:
        print(f"Error con {ticker}: {e}")
        return None


# --- HTML ---

def color_variacion(valor):
    if valor is None:
        return "#57606a", "—"
    color = "#1a7f37" if valor >= 0 else "#cf222e"
    texto = f"+{valor}%" if valor >= 0 else f"{valor}%"
    return color, texto


def generar_html(resultados):
    fecha = datetime.now().strftime("%d/%m/%Y")
    resultados_validos = [r for r in resultados if r is not None]

    favorables = [r for r in resultados_validos if r["señal"] == "Favorable"]
    precaucion = [r for r in resultados_validos if r["señal"] == "Precaución"]
    mejor = max(resultados_validos, key=lambda r: r["var_1d"], default=None)
    peor = min(resultados_validos, key=lambda r: r["var_1d"], default=None)

    def tarjeta(titulo, valor, subtitulo, color):
        return f"""
        <td style="padding:12px;">
            <div style="background:#f6f8fa;border-radius:8px;padding:16px;text-align:center;border-left:4px solid {color};">
                <div style="font-size:12px;color:#57606a;text-transform:uppercase;letter-spacing:0.5px;">{titulo}</div>
                <div style="font-size:24px;font-weight:700;color:{color};margin:4px 0;">{valor}</div>
                <div style="font-size:12px;color:#57606a;">{subtitulo}</div>
            </div>
        </td>
        """

    tarjetas = f"""
    <table width="100%" cellpadding="0" cellspacing="0"><tr>
        {tarjeta("Favorables", len(favorables), f"de {len(resultados_validos)} activos", "#1a7f37")}
        {tarjeta("Precaución", len(precaucion), "señales de alerta", "#cf222e")}
        {tarjeta("Mejor del día", mejor['ticker'] if mejor else "—", f"+{mejor['var_1d']}%" if mejor else "", "#1a7f37")}
        {tarjeta("Peor del día", peor['ticker'] if peor else "—", f"{peor['var_1d']}%" if peor else "", "#cf222e")}
    </tr></table>
    """

    filas = ""
    for i, r in enumerate(resultados_validos):
        bg = "#ffffff" if i % 2 == 0 else "#f6f8fa"
        color_1d, texto_1d = color_variacion(r["var_1d"])
        color_7d, texto_7d = color_variacion(r["var_7d"])
        color_30d, texto_30d = color_variacion(r["var_30d"])

        vol_texto = f"{r['volumen_ratio']}x" if r["volumen_ratio"] is not None else "—"
        vol_badge = " 🔥" if r["volumen_alto"] else ""

        filas += f"""
        <tr style="background:{bg};">
            <td style="padding:10px 12px;font-weight:600;">{r['ticker']}</td>
            <td style="padding:10px 12px;">${r['precio']}</td>
            <td style="padding:10px 12px;color:{color_1d};">{texto_1d}</td>
            <td style="padding:10px 12px;color:{color_7d};">{texto_7d}</td>
            <td style="padding:10px 12px;color:{color_30d};">{texto_30d}</td>
            <td style="padding:10px 12px;">{r['rsi']}</td>
            <td style="padding:10px 12px;">{r['macd_hist']}</td>
            <td style="padding:10px 12px;">{vol_texto}{vol_badge}</td>
            <td style="padding:10px 12px;">{r['volatilidad_pct']}%</td>
            <td style="padding:10px 12px;">{r['dist_max_52s']}%</td>
            <td style="padding:10px 12px;">
                <span style="background:{r['color']};color:white;padding:3px 10px;border-radius:12px;font-size:12px;font-weight:600;">
                    {r['señal']}
                </span>
            </td>
        </tr>
        """

    return f"""
    <html>
    <body style="font-family: -apple-system, Segoe UI, Arial, sans-serif; background:#ffffff; margin:0; padding:24px; color:#1f2328;">
        <h2 style="margin-bottom:4px;">📊 Análisis de mercado</h2>
        <p style="color:#57606a;margin-top:0;">{fecha}</p>

        {tarjetas}

        <div style="overflow-x:auto;margin-top:20px;">
        <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;font-size:14px;border:1px solid #d0d7de;border-radius:8px;overflow:hidden;">
            <tr style="background:#24292f;color:white;">
                <th style="padding:10px 12px;text-align:left;">Ticker</th>
                <th style="padding:10px 12px;text-align:left;">Precio</th>
                <th style="padding:10px 12px;text-align:left;">1D</th>
                <th style="padding:10px 12px;text-align:left;">7D</th>
                <th style="padding:10px 12px;text-align:left;">30D</th>
                <th style="padding:10px 12px;text-align:left;">RSI</th>
                <th style="padding:10px 12px;text-align:left;">MACD Hist</th>
                <th style="padding:10px 12px;text-align:left;">Vol.</th>
                <th style="padding:10px 12px;text-align:left;">Volatilidad</th>
                <th style="padding:10px 12px;text-align:left;">vs Máx 52s</th>
                <th style="padding:10px 12px;text-align:left;">Señal</th>
            </tr>
            {filas}
        </table>
        </div>

        <div style="margin-top:20px;font-size:12px;color:#57606a;line-height:1.6;">
            <p><strong>Vol.</strong> = volumen de hoy respecto al promedio de 20 días (🔥 = volumen inusualmente alto, &gt;1.5x).</p>
            <p><strong>Volatilidad</strong> = ATR(14) como % del precio actual (mayor = movimientos más amplios de lo normal).</p>
            <p><strong>vs Máx 52s</strong> = qué tan lejos está el precio actual de su máximo de las últimas 52 semanas.</p>
            <p style="margin-top:12px;">Generado automáticamente. No constituye asesoría financiera.</p>
        </div>
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

    if all(k in os.environ for k in ("GMAIL_USER", "GMAIL_PASS", "DESTINATARIO")):
        fecha = datetime.now().strftime("%d/%m/%Y")
        enviar_correo(f"Análisis de mercado — {fecha}", html)
        print("Correo enviado correctamente.")
    else:
        print("Variables GMAIL_USER/GMAIL_PASS/DESTINATARIO no configuradas — solo se generó preview.html (modo prueba).")
