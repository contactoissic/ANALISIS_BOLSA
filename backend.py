import yfinance as yf
import pandas as pd
import pandas_ta as ta
from datetime import datetime

# ─────────────────────────────────────────────
#  MOTOR DUAL: SWING (Corto plazo) + VALUE (Largo plazo)
#  + DIVIDENDOS + MONEDA
# ─────────────────────────────────────────────

def analizar_swing(ticker_raw: str) -> dict:
    """Estrategia de Corto Plazo: EMA 9/21, MACD, Volumen."""
    ticker = str(ticker_raw).strip().split(',')[0].split(' ')[0].upper()
    try:
        t = yf.Ticker(ticker)
        df = t.history(period="6mo")
        info = t.info
        moneda = info.get("currency", "USD")
    except:
        return {"error": f"No se pudo obtener {ticker}"}

    if df.empty or len(df) < 30:
        return {"error": f"Datos insuficientes para {ticker}"}

    df = df.copy()
    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)

    df.ta.ema(length=9,  append=True)
    df.ta.ema(length=21, append=True)
    df.ta.rsi(length=14, append=True)
    df.ta.atr(length=14, append=True)
    df.ta.macd(fast=12, slow=26, signal=9, append=True)

    ultimo   = float(df['Close'].iloc[-1])
    anterior = float(df['Close'].iloc[-2]) if len(df) > 1 else ultimo
    var_pct  = ((ultimo - anterior) / anterior) * 100

    ema9  = float(df['EMA_9'].iloc[-1])  if 'EMA_9'  in df.columns else ultimo
    ema21 = float(df['EMA_21'].iloc[-1]) if 'EMA_21' in df.columns else ultimo
    rsi   = float(df['RSI_14'].iloc[-1]) if 'RSI_14' in df.columns else 50.0
    atr   = float(df['ATRr_14'].iloc[-1]) if 'ATRr_14' in df.columns else 1.0
    macd_val  = float(df['MACD_12_26_9'].iloc[-1])  if 'MACD_12_26_9'  in df.columns else 0.0
    macd_sig  = float(df['MACDs_12_26_9'].iloc[-1]) if 'MACDs_12_26_9' in df.columns else 0.0

    try:
        vol_avg = float(df['Volume'].tail(20).mean())
        vol_hoy = float(df['Volume'].iloc[-1])
        vol_rel = round(vol_hoy / vol_avg, 2) if vol_avg > 0 else 1.0
    except:
        vol_rel = 1.0

    try:
        grafico_30d = [float(x) for x in df['Close'].tail(30).values]
        if len(grafico_30d) < 2: grafico_30d = [ultimo, ultimo]
    except:
        grafico_30d = [ultimo, ultimo]

    stop_loss = round(ultimo - (2 * atr), 2)
    riesgo    = ultimo - stop_loss
    target    = round(ultimo + 3 * riesgo, 2)

    # SCORING SWING (HIGH MOMENTUM / BREAKOUT)
    # En lugar de comprar acciones que caen (RSI bajo), buscamos subidas verticales
    score = 0
    if ema9 > ema21:           score += 20   # Tendencia de corto plazo alcista confirmada
    if macd_val > macd_sig:    score += 20   # Momentum acelerando (Aceleración de precios)
    if macd_val > 0:           score += 10   # Territorio netamente alcista (toros al mando)
    
    # RSI Dulce para Momentum: Entre 55 y 72 (Subiendo fuerte, pero sin estar quemada)
    if 55 <= rsi <= 72:        score += 30   # Zona de explosión / Breakout
    elif rsi > 72:             score -= 20   # Demasiado tarde, sobrecomprado extremo
    elif rsi < 45:             score -= 20   # Tendencia bajista activa (cuchillo cayendo)
    
    if vol_rel > 1.3:          score += 20   # Volumen institucional empujando el precio

    score = min(max(score, 0), 100)
    if score >= 75:   semaforo = "🟢 COMPRA (MOMENTUM)"; accion = "SUBIRSE AL COHETE"
    elif score >= 50: semaforo = "🟡 VIGILAR TENDENCIA"; accion = "FALTA FUERZA"
    else:             semaforo = "🔴 EVITAR / CAÍDA";    accion = "TENDENCIA MUERTA"

    return {
        "Ticker": ticker, "Moneda": moneda, "Modo": "SWING",
        "Grafico_30d": grafico_30d,
        "Precio": round(ultimo, 2), "Variacion_%": round(var_pct, 2),
        "EMA9": round(ema9, 2), "EMA21": round(ema21, 2),
        "RSI_14": round(rsi, 2), "MACD": round(macd_val, 4),
        "Vol_Relativo": vol_rel,
        "Stop_Loss": stop_loss, "Target": target,
        "Score": score, "Semaforo": semaforo, "Accion": accion,
    }


def analizar_value(ticker_raw: str) -> dict:
    """Estrategia de Largo Plazo: SMA 50/200, P/E, Deuda/Capital."""
    ticker = str(ticker_raw).strip().split(',')[0].split(' ')[0].upper()
    try:
        t = yf.Ticker(ticker)
        df = t.history(period="3y")
        info = t.info
        moneda      = info.get("currency", "USD")
        per         = info.get("trailingPE",  info.get("forwardPE", None))
        per         = round(float(per), 2) if per else "N/A"
        debt_equity = info.get("debtToEquity", None)
        debt_equity = round(float(debt_equity) / 100, 2) if debt_equity else "N/A"
        div_yield   = info.get("dividendYield", 0)
        div_yield   = round(float(div_yield) * 100, 2) if div_yield else 0.0
    except:
        return {"error": f"No se pudo obtener info fundamental de {ticker}"}

    if df.empty or len(df) < 150:
        return {"error": f"Historial insuficiente para análisis Value de {ticker}"}

    df = df.copy()
    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)

    df.ta.sma(length=50,  append=True)
    df.ta.sma(length=200, append=True)
    df.ta.rsi(length=14,  append=True)
    df.ta.atr(length=14,  append=True)

    ultimo   = float(df['Close'].iloc[-1])
    anterior = float(df['Close'].iloc[-2]) if len(df) > 1 else ultimo
    var_pct  = ((ultimo - anterior) / anterior) * 100

    sma50  = float(df['SMA_50'].iloc[-1])  if 'SMA_50'  in df.columns else ultimo
    sma200 = float(df['SMA_200'].iloc[-1]) if 'SMA_200' in df.columns else ultimo
    rsi    = float(df['RSI_14'].iloc[-1])  if 'RSI_14'  in df.columns else 50.0
    atr    = float(df['ATRr_14'].iloc[-1]) if 'ATRr_14' in df.columns else 1.0

    try:
        grafico_30d = [float(x) for x in df['Close'].tail(30).values]
        if len(grafico_30d) < 2: grafico_30d = [ultimo, ultimo]
    except:
        grafico_30d = [ultimo, ultimo]

    stop_loss = round(ultimo - (2 * atr), 2)
    riesgo    = ultimo - stop_loss
    target    = round(ultimo + 3 * riesgo, 2)

    # SCORING VALUE
    score = 0
    if ultimo > sma200:       score += 30   # Tendencia estructural alcista
    if ultimo > sma50:        score += 15   # Sub-tendencia alcista
    if rsi < 45:              score += 20   # Retroceso sano (Oportunidad)
    if isinstance(per, float):
        if per < 20:          score += 20   # Empresa Barata Fundamentalmente
        elif per < 35:        score += 10
        else:                 score -= 5    # Cara
    if div_yield > 1.5:       score += 10   # Renta Pasiva atractiva
    if isinstance(debt_equity, float) and debt_equity < 1: score += 5

    score = min(score, 100)
    if score >= 70:   semaforo = "🟢 COMPRA VALUE"; accion = "ACUMULACIÓN ESTRATÉGICA"
    elif score >= 40: semaforo = "🟡 MANTENER";      accion = "NEUTRAL LARGO PLAZO"
    else:             semaforo = "🔴 EVITAR";         accion = "FUNDAMENTALES DÉBILES"

    return {
        "Ticker": ticker, "Moneda": moneda, "Modo": "VALUE",
        "Grafico_30d": grafico_30d,
        "Precio": round(ultimo, 2), "Variacion_%": round(var_pct, 2),
        "SMA_50": round(sma50, 2), "SMA_200": round(sma200, 2),
        "RSI_14": round(rsi, 2), "PER": per,
        "Deuda_Capital": debt_equity, "Dividendo_%": div_yield,
        "Stop_Loss": stop_loss, "Target": target,
        "Score": score, "Semaforo": semaforo, "Accion": accion,
    }


def obtener_dividendos(ticker_raw: str) -> dict:
    """Extrae info de dividendos: yield, frecuencia, próximo pago."""
    ticker = str(ticker_raw).strip().split(',')[0].split(' ')[0].upper()
    try:
        t = yf.Ticker(ticker)
        info = t.info
        nombre     = info.get("longName", ticker)
        moneda     = info.get("currency", "USD")
        yield_pct  = info.get("dividendYield", 0)
        yield_pct  = round(float(yield_pct) * 100, 2) if yield_pct else 0.0
        div_rate   = info.get("dividendRate", 0) or 0.0
        ex_date    = info.get("exDividendDate", None)
        frecuencia = info.get("dividendFrequency", "N/A")
        freq_map   = {1: "Anual", 2: "Semi-anual", 4: "Trimestral", 12: "Mensual"}
        frecuencia = freq_map.get(frecuencia, str(frecuencia))
        ex_date_str = datetime.fromtimestamp(ex_date).strftime("%Y-%m-%d") if ex_date else "N/A"
        paga_div = yield_pct > 0
        return {
            "Ticker": ticker, "Nombre": nombre, "Moneda": moneda,
            "Paga_Dividendos": "✅ SÍ" if paga_div else "❌ NO",
            "Yield_Anual_%": yield_pct,
            "Dividendo_x_Accion": round(div_rate, 4),
            "Frecuencia": frecuencia,
            "Ex-Dividend_Date": ex_date_str,
        }
    except:
        return {"Ticker": ticker, "Paga_Dividendos": "❌ NO", "Yield_Anual_%": 0}
