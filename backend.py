import yfinance as yf
import pandas as pd
from datetime import datetime

# ─────────────────────────────────────────────
#  INDICADORES TÉCNICOS NATIVOS (PANDAS PURO)
# ─────────────────────────────────────────────

def add_ema(df, length, column='Close'):
    df[f'EMA_{length}'] = df[column].ewm(span=length, adjust=False).mean()

def add_sma(df, length, column='Close'):
    df[f'SMA_{length}'] = df[column].rolling(window=length).mean()

def add_rsi(df, length=14, column='Close'):
    delta = df[column].diff()
    up, down = delta.clip(lower=0), -1 * delta.clip(upper=0)
    ema_up = up.ewm(com=length - 1, adjust=False).mean()
    ema_down = down.ewm(com=length - 1, adjust=False).mean()
    rs = ema_up / ema_down
    df[f'RSI_{length}'] = 100 - (100 / (1 + rs))

def add_macd(df, fast=12, slow=26, signal=9, column='Close'):
    ema_fast = df[column].ewm(span=fast, adjust=False).mean()
    ema_slow = df[column].ewm(span=slow, adjust=False).mean()
    df[f'MACD_{fast}_{slow}_{signal}'] = ema_fast - ema_slow
    df[f'MACDs_{fast}_{slow}_{signal}'] = df[f'MACD_{fast}_{slow}_{signal}'].ewm(span=signal, adjust=False).mean()

def add_atr(df, length=14):
    high_low = df['High'] - df['Low']
    high_close = (df['High'] - df['Close'].shift()).abs()
    low_close = (df['Low'] - df['Close'].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    # Wilder's smoothing method (alpha = 1/length)
    df[f'ATRr_{length}'] = tr.ewm(alpha=1/length, adjust=False).mean()


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

    add_ema(df, 9)
    add_ema(df, 21)
    add_rsi(df, 14)
    add_atr(df, 14)
    add_macd(df, 12, 26, 9)

    ultimo   = float(df['Close'].iloc[-1])
    anterior = float(df['Close'].iloc[-2]) if len(df) > 1 else ultimo
    var_pct  = ((ultimo - anterior) / anterior) * 100

    ema9  = float(df['EMA_9'].iloc[-1])  if pd.notna(df['EMA_9'].iloc[-1])  else ultimo
    ema21 = float(df['EMA_21'].iloc[-1]) if pd.notna(df['EMA_21'].iloc[-1]) else ultimo
    rsi   = float(df['RSI_14'].iloc[-1]) if pd.notna(df['RSI_14'].iloc[-1]) else 50.0
    atr   = float(df['ATRr_14'].iloc[-1]) if pd.notna(df['ATRr_14'].iloc[-1]) else 1.0
    macd_val  = float(df['MACD_12_26_9'].iloc[-1])  if pd.notna(df['MACD_12_26_9'].iloc[-1])  else 0.0
    macd_sig  = float(df['MACDs_12_26_9'].iloc[-1]) if pd.notna(df['MACDs_12_26_9'].iloc[-1]) else 0.0

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
    score = 0
    if ema9 > ema21:           score += 20   
    if macd_val > macd_sig:    score += 20   
    if macd_val > 0:           score += 10   
    
    if 55 <= rsi <= 72:        score += 30   
    elif rsi > 72:             score -= 20   
    elif rsi < 45:             score -= 20   
    
    if vol_rel > 1.3:          score += 20   

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

    add_sma(df, 50)
    add_sma(df, 200)
    add_rsi(df, 14)
    add_atr(df, 14)

    ultimo   = float(df['Close'].iloc[-1])
    anterior = float(df['Close'].iloc[-2]) if len(df) > 1 else ultimo
    var_pct  = ((ultimo - anterior) / anterior) * 100

    sma50  = float(df['SMA_50'].iloc[-1])  if pd.notna(df['SMA_50'].iloc[-1])  else ultimo
    sma200 = float(df['SMA_200'].iloc[-1]) if pd.notna(df['SMA_200'].iloc[-1]) else ultimo
    rsi    = float(df['RSI_14'].iloc[-1])  if pd.notna(df['RSI_14'].iloc[-1])  else 50.0
    atr    = float(df['ATRr_14'].iloc[-1]) if pd.notna(df['ATRr_14'].iloc[-1]) else 1.0

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
    if ultimo > sma200:       score += 30   
    if ultimo > sma50:        score += 15   
    if rsi < 45:              score += 20   
    if isinstance(per, float):
        if per < 20:          score += 20   
        elif per < 35:        score += 10
        else:                 score -= 5    
    if div_yield > 1.5:       score += 10   
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
