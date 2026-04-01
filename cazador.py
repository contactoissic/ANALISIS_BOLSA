import streamlit as st
import yfinance as yf
import pandas as pd
from backend import analizar_swing, analizar_value, obtener_dividendos
from concurrent.futures import ThreadPoolExecutor

# Catálogo de CORTO PLAZO (High Beta, Cripto, Tech y Momentum)
TICKERS_SWING = [
    # Cripto directas (Alta volatilidad)
    "BTC-USD", "ETH-USD", "SOL-USD", "DOGE-USD", "ADA-USD", "XRP-USD", "AVAX-USD", "LINK-USD", "DOT-USD",
    
    # High Beta / Alto Momentum / Riesgo (Las que dan retornos explosivos rápidos)
    "PLTR", "MSTR", "SMCI", "COIN", "CRWD", "MARA", "UBER", "MELI", "NU",
    "CVNA", "RST", "HOOD", "AFRM", "PATH", "SOFI", "SNOW", "RBLX", "DDOG", 
    "DKNG", "UPST", "RIOT", "LCID", "RIVN", "PYPL", "SQ", "SHOP", "SPOT",
    
    # Tech Megacaps y Chips (Tienen gran volumen direccional)
    "NVDA", "TSLA", "AMD", "META", "AMZN", "NFLX", "GOOGL", "MSFT", "AAPL",
    "INTC", "MU", "QCOM", "AVGO", "ARM", "TSM",
    
    # ETFs e Índices Apalancados y Volátiles
    "TQQQ", "SOXL", "QQQ", "SPY", "ARKK", "ARKG", "ARKF", "IWM"
]

# Catálogo de LARGO PLAZO (Megacaps de Valor, Dividendos, Finanzas, Industriales)
TICKERS_VALUE = [
    # Megacaps / Seguras / Consumo Básico
    "AAPL", "MSFT", "GOOGL", "AMZN", "BRK-B", "WMT", "COST", "TGT", "PG", 
    "KO", "PEP", "HD", "MCD", "SBUX", "NKE", "DIS", "VZ", "T", "CMCSA",
    
    # Finanzas (Acorazados y Bancos)
    "JPM", "V", "MA", "BAC", "GS", "WFC", "C", "AXP", "MS", "BLK",
    
    # Salud y Farmacéuticas
    "LLY", "UNH", "JNJ", "ABBV", "MRK", "PFE", "NVO", "AMGN", "CVS", "ISRG",
    
    # Industriales
    "GE", "BA", "CAT", "MMM", "HON", "LMT", "RTX", "UPS", "FDX", "DE",
    
    # Energía y Materiales
    "XOM", "CVX", "COP", "SLB", "OXY", "FCX", "NEM",
    
    # ETFs Globales y de Dividendos
    "SPY", "VOO", "VTI", "SCHD", "VYM", "VNQ", "GLD", "SLV", "DIA", "EFA",
    
    # Mercado Mexicano (Estables locales en la BMV/BIVA)
    "WALMEX.MX", "FEMSAUBD.MX", "BIMBOA.MX", "AMX", "CEMEXCPO.MX", "GFNORTEO.MX",
    "GMEXICOB.MX", "GAPB.MX", "ASURB.MX", "OMAB.MX", "ELEKTRA.MX", "GRUMAB.MX",
    "KOFUBL.MX", "ALFAA.MX", "PE&OLES.MX"
]

TICKERS_DIVIDENDOS = [
    "KO","PEP","JNJ","PG","MCD","T","VZ","XOM","CVX","ABBV",
    "MO","PM","O","WMT","HD","MSFT","AAPL","V","JPM","GS",
    "WALMEX.MX","FEMSAUBD.MX","BIMBOA.MX","GFNORTEO.MX",
]


def _run_parallel(fn, tickers):
    resultados = []
    def _proc(ticker):
        try:
            res = fn(ticker)
            return None if "error" in res else res
        except:
            return None
    import time
    with ThreadPoolExecutor(max_workers=3) as ex:
        def _proc(ticker):
            try:
                # Agregamos micro-pausa para engañar al sistema anti-bot de Yahoo
                time.sleep(0.5)
                res = fn(ticker)
                return None if "error" in res else res
            except:
                return None
        for r in ex.map(_proc, tickers):
            if r:
                resultados.append(r)
    return pd.DataFrame(resultados)


# ── CACHÉ DE STREAMLIT: Los resultados se guardan 5 minutos en RAM ──
# La primera carga tarda ~10s. Las siguientes son INSTANTÁNEAS hasta que pasen 5 min.

@st.cache_data(ttl=300, show_spinner=False)
def buscar_swing_trading():
    df = _run_parallel(analizar_swing, TICKERS_SWING)
    if df.empty:
        return pd.DataFrame(), pd.DataFrame()
    cols = ["Ticker","Moneda","Grafico_30d","Semaforo","Score","Precio","Variacion_%","RSI_14","EMA9","EMA21","MACD","Vol_Relativo","Stop_Loss","Accion"]
    cols = [c for c in cols if c in df.columns]
    df = df[cols]
    comprar = df[df["Score"] >= 50].sort_values("Score", ascending=False).head(30)
    vender  = df[df["Score"] <  40].sort_values("Score", ascending=True).head(30)
    return comprar, vender


@st.cache_data(ttl=300, show_spinner=False)
def buscar_value_investing():
    df = _run_parallel(analizar_value, TICKERS_VALUE)
    if df.empty:
        return pd.DataFrame(), pd.DataFrame()
    cols = ["Ticker","Moneda","Grafico_30d","Semaforo","Score","Precio","Variacion_%","PER","Dividendo_%","Deuda_Capital","SMA_50","SMA_200","RSI_14","Stop_Loss","Accion"]
    cols = [c for c in cols if c in df.columns]
    df = df[cols]
    comprar = df[df["Score"] >= 50].sort_values("Score", ascending=False).head(30)
    vender  = df[df["Score"] <  40].sort_values("Score", ascending=True).head(30)
    return comprar, vender


@st.cache_data(ttl=600, show_spinner=False)
def buscar_dividendos():
    df = _run_parallel(obtener_dividendos, TICKERS_DIVIDENDOS)
    if df.empty:
        return pd.DataFrame()
    return df[df["Yield_Anual_%"] > 0].sort_values("Yield_Anual_%", ascending=False)


@st.cache_data(ttl=60, show_spinner=False)
def analisis_individual_swing(ticker: str):
    return analizar_swing(ticker)


@st.cache_data(ttl=60, show_spinner=False)
def analisis_individual_value(ticker: str):
    return analizar_value(ticker)


@st.cache_data(ttl=30, show_spinner=False)
def obtener_tipo_cambio():
    try:
        info = yf.Ticker("MXN=X").fast_info
        return round(float(info['lastPrice']), 2)
    except:
        return 17.50


def _obtener_dividendo_ticker(ticker: str) -> dict:
    """Extrae dividendo por acción y frecuencia de pago de un ticker."""
    try:
        info = yf.Ticker(ticker).info
        div_rate  = float(info.get("dividendRate", 0) or 0)      # Dividendo anual por acción
        freq_num  = info.get("dividendFrequency", None)           # 1=Anual, 4=Trimestral, 12=Mensual
        freq_map  = {1: ("Anual", 1), 2: ("Semi-anual", 2), 4: ("Trimestral", 4), 12: ("Mensual", 12)}
        freq_label, freq_n = freq_map.get(freq_num, ("N/A", 1))
        div_por_pago = div_rate / freq_n if freq_n and div_rate else 0
        return {"div_anual": div_rate, "div_por_pago": div_por_pago, "frecuencia": freq_label}
    except:
        return {"div_anual": 0, "div_por_pago": 0, "frecuencia": "N/A"}


def analizar_cartera_viva(df_historial):
    """Sin caché porque los precios de la cartera personal deben ser siempre frescos."""
    from backend import analizar_swing as sw
    datos = []
    if df_historial.empty:
        return pd.DataFrame()
    for _, row in df_historial.iterrows():
        ticker        = row['ticker']
        precio_compra = float(row['precio_ejecucion'])
        cantidad      = float(row['cantidad'])
        invertido     = float(row['monto_total'])
        estrategia    = str(row.get('estrategia', 'SWING')).upper()
        objetivo_pct  = float(row.get('objetivo_pct', 10.0))

        try:
            t = yf.Ticker(ticker)
            precio_actual = float(t.fast_info['lastPrice'])
            moneda        = str(t.fast_info.get('currency', 'USD'))
        except:
            precio_actual = precio_compra
            moneda        = "N/A"

        valor_actual   = precio_actual * cantidad
        rendimiento    = valor_actual - invertido
        comision       = (invertido + valor_actual) * 0.0025
        ganancia_bruta = rendimiento - comision
        isr            = (ganancia_bruta * 0.10) if ganancia_bruta > 0 else 0.0
        neto           = ganancia_bruta - isr
        roi            = (neto / invertido * 100) if invertido > 0 else 0

        # ── Alerta Swing: ¿Llegó al objetivo? ──
        precio_objetivo = round(precio_compra * (1 + objetivo_pct / 100), 4)
        objetivo_alcanzado = precio_actual >= precio_objetivo if estrategia == "SWING" else False
        alerta_swing = "🔔 ¡VENDER AHORA!" if objetivo_alcanzado else (
            f"Objetivo: {precio_objetivo:.2f}" if estrategia == "SWING" else "—"
        )

        # ── Dividendos ──
        div_info         = _obtener_dividendo_ticker(ticker)
        div_anual_total  = round(div_info["div_anual"] * cantidad, 4)
        div_pago_total   = round(div_info["div_por_pago"] * cantidad, 4)
        div_frecuencia   = div_info["frecuencia"]
        div_neto_anual   = round(div_anual_total * 0.90, 4)

        try:
            recom = sw(ticker).get("Accion", "N/A")
        except:
            recom = "N/A"

        datos.append({
            "Estrategia": estrategia,
            "Ticker": ticker, "Moneda": moneda, "Cant": cantidad,
            "Costo_Base": precio_compra, "Precio_Hoy": precio_actual,
            "Obj_%": objetivo_pct if estrategia == "SWING" else "—",
            "Alerta": alerta_swing,
            "Invertido": invertido, "Valor_Actual": valor_actual,
            "Tax+GBM": round(comision + isr, 2),
            "NETO_$": round(neto, 2), "ROI_%": round(roi, 2),
            "Div_x_Pago": div_pago_total if div_pago_total > 0 else "—",
            "Frecuencia_Pago": div_frecuencia if div_anual_total > 0 else "No paga",
            "Div_Anual_NETO": div_neto_anual if div_neto_anual > 0 else "—",
            "IA_Dice": recom,
        })
    return pd.DataFrame(datos)


