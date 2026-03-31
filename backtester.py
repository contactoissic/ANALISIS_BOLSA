"""
╔══════════════════════════════════════════════════════════╗
║  BACKTESTER: Motor de Simulación Histórica               ║
║  Estrategia: RSI < 40 = COMPRA / Precio toca Target = VENTA  ║
║  Capital Fijo por operación (configurable)              ║
╚══════════════════════════════════════════════════════════╝
"""

import yfinance as yf
import pandas as pd
from backend import add_ema, add_sma, add_rsi, add_atr
from datetime import datetime

COMISION_GBM = 0.0025   # 0.25% por lado
ISR_TASA      = 0.10    # 10% sobre ganancias


def ejecutar_backtest(ticker: str, capital_inicial: float, pct_por_trade: float,
                      periodo: str = "2y", objetivo_pct: float = 15.0,
                      stop_pct: float = 7.0, modo: str = "SWING") -> dict:
    """
    Simula el algoritmo Swing o Value sobre datos históricos reales, incluyendo cobro de dividendos.

    Parámetros:
    - ticker           : Símbolo bursátil (ej: "AAPL")
    - capital_inicial  : Fondo total disponible en su moneda local
    - pct_por_trade    : % del capital a invertir por operación (ej: 20 = usa 20% del fondo)
    - periodo          : Período histórico ("1y", "2y", "3y")
    - objetivo_pct     : % de ganancia para cerrar la posición (SELL)
    - stop_pct         : % de pérdida máxima para cortar la pérdida (Stop-Loss)
    - modo             : "SWING" (corto plazo) o "VALUE" (largo plazo)
    """
    # ── Descargar datos históricos ──
    t = yf.Ticker(ticker)
    df = t.history(period=periodo, interval="1d", actions=True)
    moneda = t.info.get("currency", "USD") if hasattr(t, 'info') else "USD"

    if df.empty or len(df) < 60:
        return {"error": f"Datos insuficientes para {ticker}. Mínimo 60 días de historial."}

    df = df.copy()
    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)

    # ── Calcular Indicadores ──
    add_rsi(df, length=14)
    add_ema(df, length=9)
    add_ema(df, length=21)
    add_sma(df, length=50)
    add_sma(df, length=200)
    add_atr(df, length=14)
    df.dropna(inplace=True)

    # ── Motor de Simulación ──
    capital          = capital_inicial
    posicion_activa  = False  # ¿Estamos comprados ahora?
    precio_entrada   = 0.0
    cantidad_acciones = 0.0
    capital_en_trade  = 0.0

    operaciones      = []       # Registro de cada trade
    equity_curve     = []       # Curva de valor del portafolio en el tiempo

    for fecha, row in df.iterrows():
        close  = float(row['Close'])
        rsi    = float(row.get('RSI_14', 50))
        ema9   = float(row.get('EMA_9', close))
        ema21  = float(row.get('EMA_21', close))
        sma50  = float(row.get('SMA_50', close))
        sma200 = float(row.get('SMA_200', close))
        atr    = float(row.get('ATRr_14', close * 0.01))
        div_x  = float(row.get('Dividends', 0.0))

        # 💲 Cobrar Dividendos si estamos posicionados 💲
        if posicion_activa and div_x > 0:
            ganancia_div = cantidad_acciones * div_x * (1 - ISR_TASA)  # Dividendo Neto
            capital += ganancia_div
            operaciones.append({
                "Fecha": fecha, "Acción": "💵 COBRO DIVIDENDOS",
                "Precio": round(close, 4), "Cant.": round(cantidad_acciones, 4),
                "Capital_Usado": round(capital_en_trade, 2),
                "Capital_Libre": round(capital, 2),
                "Resultado_$": round(ganancia_div, 2), "Resultado_%": "—"
            })

        valor_total = capital + (cantidad_acciones * close if posicion_activa else 0)

        if not posicion_activa:
            # ── SEÑAL DE COMPRA DEPENDIENDO DEL MODO ──
            comprar = False
            if modo == "SWING":
                # Momentum puro: RSI sano y EMAs alcistas
                if 55 <= rsi <= 75 and ema9 > ema21: comprar = True
            else: # VALUE
                # Compra en cruce sano: Precio encima de SMA 200 pero RSI no eufórico
                if close > sma200 and rsi < 60: comprar = True

            if comprar:
                capital_a_usar   = capital * (pct_por_trade / 100)
                comision_entrada = capital_a_usar * COMISION_GBM
                capital_neto     = capital_a_usar - comision_entrada
                cantidad_acciones = capital_neto / close
                capital_en_trade  = capital_a_usar
                precio_entrada    = close
                precio_objetivo   = close * (1 + objetivo_pct / 100)
                precio_stop       = close * (1 - stop_pct / 100)
                capital          -= capital_a_usar
                posicion_activa   = True
                operaciones.append({
                    "Fecha": fecha, "Acción": "🟢 COMPRA",
                    "Precio": round(close, 4), "Cant.": round(cantidad_acciones, 4),
                    "Capital_Usado": round(capital_a_usar, 2),
                    "Capital_Libre": round(capital, 2),
                    "Resultado_$": "—", "Resultado_%": "—"
                })

        else:
            # ── SEÑAL DE VENTA: Objetivo o Stop-Loss ──
            toco_objetivo = close >= precio_objetivo
            toco_stop     = close <= precio_stop

            if toco_objetivo or toco_stop:
                valor_venta      = cantidad_acciones * close
                comision_salida  = valor_venta * COMISION_GBM
                ganancia_bruta   = valor_venta - capital_en_trade - comision_salida
                isr              = ganancia_bruta * ISR_TASA if ganancia_bruta > 0 else 0
                ganancia_neta    = ganancia_bruta - isr
                capital         += capital_en_trade + ganancia_neta
                pct_result       = (ganancia_neta / capital_en_trade) * 100
                motivo           = "🎯 Objetivo" if toco_objetivo else "🛑 Stop-Loss"
                operaciones.append({
                    "Fecha": fecha, "Acción": f"🔴 VENTA ({motivo})",
                    "Precio": round(close, 4), "Cant.": round(cantidad_acciones, 4),
                    "Capital_Usado": round(capital_en_trade, 2),
                    "Capital_Libre": round(capital, 2),
                    "Resultado_$": round(ganancia_neta, 2),
                    "Resultado_%": round(pct_result, 2)
                })
                posicion_activa   = False
                cantidad_acciones = 0.0
                capital_en_trade  = 0.0

        # Registrar curva de equity en cada punto
        equity_curve.append({
            "Fecha": fecha,
            "Valor_Total": round(capital + (cantidad_acciones * close if posicion_activa else 0), 2),
            "Capital_Libre": round(capital, 2),
        })

    # ── Estadísticas Finales ──
    df_ops   = pd.DataFrame(operaciones)
    df_eq    = pd.DataFrame(equity_curve)

    valor_final    = equity_curve[-1]["Valor_Total"] if equity_curve else capital_inicial
    rendimiento    = valor_final - capital_inicial
    roi_total_pct  = (rendimiento / capital_inicial) * 100

    ventas = [op for op in operaciones if "VENTA" in op["Acción"]]
    wins   = [op for op in ventas if isinstance(op["Resultado_$"], float) and op["Resultado_$"] > 0]
    losses = [op for op in ventas if isinstance(op["Resultado_$"], float) and op["Resultado_$"] <= 0]
    win_rate = (len(wins) / len(ventas) * 100) if ventas else 0
    mejor_trade = max([op["Resultado_%"] for op in ventas if isinstance(op["Resultado_%"], float)], default=0)
    peor_trade  = min([op["Resultado_%"] for op in ventas if isinstance(op["Resultado_%"], float)], default=0)

    return {
        "Ticker": ticker,
        "Moneda": moneda,
        "Capital_Inicial": capital_inicial,
        "Valor_Final": round(valor_final, 2),
        "Rendimiento_$": round(rendimiento, 2),
        "ROI_%": round(roi_total_pct, 2),
        "Total_Trades": len(ventas),
        "Trades_Ganadores": len(wins),
        "Trades_Perdedores": len(losses),
        "Win_Rate_%": round(win_rate, 2),
        "Mejor_Trade_%": round(mejor_trade, 2),
        "Peor_Trade_%": round(peor_trade, 2),
        "df_operaciones": df_ops,
        "df_equity": df_eq,
        "error": None,
    }


def ejecutar_backtest_multiticker(tickers: list, capital_mxn_inicial: float,
                                  periodo: str = "2y", objetivo_pct: float = 12.0,
                                  stop_pct: float = 7.0) -> dict:
    """
    Toma un capital total, lo divide equitativamente entre los tickers y simula el portafolio combinado.
    """
    if not tickers:
        return {"error": "No se proporcionaron tickers para simular."}
    
    capital_por_ticker = capital_mxn_inicial / len(tickers)
    resultados = []
    
    for tk in tickers:
        res = ejecutar_backtest(tk, capital_inicial=capital_por_ticker, pct_por_trade=100.0,
                                periodo=periodo, objetivo_pct=objetivo_pct, stop_pct=stop_pct)
        if not res.get("error"):
            resultados.append(res)
            
    if not resultados:
        return {"error": "Ningún ticker tuvo datos suficientes para la simulación."}
        
    # Agrupar estadísticas
    total_trades = sum([r["Total_Trades"] for r in resultados])
    trades_gani  = sum([r["Trades_Ganadores"] for r in resultados])
    
    # Combinar curvas de equity
    df_eq_comb = pd.DataFrame()
    for r in resultados:
        df_e = r["df_equity"].copy()
        df_e.set_index("Fecha", inplace=True)
        # Queremos solo el valor total
        series_v = df_e["Valor_Total"].rename(r["Ticker"])
        if df_eq_comb.empty:
            df_eq_comb = pd.DataFrame(series_v)
        else:
            df_eq_comb = df_eq_comb.join(series_v, how="outer")
            
    # Rellenar huecos (por feriados distintos o salidas a bolsa)
    df_eq_comb.fillna(method="ffill", inplace=True)
    df_eq_comb.fillna(capital_por_ticker, inplace=True)
    # Sumar todas las columnas para obtener el valor del portafolio total en cada día
    df_eq_comb["Valor_Portafolio"] = df_eq_comb.sum(axis=1)
    df_eq_comb.reset_index(inplace=True)
    
    valor_final = float(df_eq_comb["Valor_Portafolio"].iloc[-1])
    rendimiento = valor_final - capital_mxn_inicial
    roi_total   = (rendimiento / capital_mxn_inicial) * 100
    
    # Combinar operaciones
    lista_ops = []
    for r in resultados:
        df_o = r["df_operaciones"].copy()
        if not df_o.empty:
            df_o["Ticker"] = r["Ticker"]
            lista_ops.append(df_o)
            
    if lista_ops:
        df_ops_comb = pd.concat(lista_ops, ignore_index=True)
        df_ops_comb.sort_values("Fecha", inplace=True)
    else:
        df_ops_comb = pd.DataFrame()
        
    return {
        "Capital_Inicial": capital_mxn_inicial,
        "Valor_Final": round(valor_final, 2),
        "Rendimiento_$": round(rendimiento, 2),
        "ROI_%": round(roi_total, 2),
        "Total_Trades": total_trades,
        "Win_Rate_%": round((trades_gani / total_trades * 100) if total_trades else 0, 2),
        "df_equity": df_eq_comb,
        "df_operaciones": df_ops_comb,
        "tickers_incluidos": [r["Ticker"] for r in resultados],
        "error": None
    }
