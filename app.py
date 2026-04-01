import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from database import (init_db, registrar_operacion, obtener_historial_df,
                      limpiar_boveda, eliminar_operacion_por_ticker, vender_parcial)
from cazador import (buscar_swing_trading, buscar_value_investing, buscar_dividendos,
                     analizar_cartera_viva, analisis_individual_swing,
                     analisis_individual_value, obtener_tipo_cambio)
from backtester import ejecutar_backtest, ejecutar_backtest_multiticker

init_db()

# ═══════════════════════════════════════════════════════
#  CONFIGURACIÓN GLOBAL
# ═══════════════════════════════════════════════════════
st.set_page_config(page_title="ANALISIS_BOLSA | HQ Terminal", layout="wide", initial_sidebar_state="collapsed", page_icon="📈")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;900&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }

.hq-metric { background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
  border: 1px solid #0f3460; border-radius: 12px; padding: 18px 22px; text-align: center; height: 100%; }
.hq-metric .label { font-size: 0.75rem; color: #8892b0; letter-spacing: 2px; text-transform: uppercase; margin-bottom: 6px; }
.hq-metric .value { font-size: 1.8rem; font-weight: 800; color: #e6f1ff; line-height: 1; }
.hq-metric .sub { font-size: 0.85rem; color: #64ffda; margin-top: 4px; }

.verde-card  { background: linear-gradient(135deg,#00251a,#003d29); border:2px solid #00C853; border-radius:12px; padding:18px; text-align:center; }
.amarillo-card { background: linear-gradient(135deg,#2a2000,#3d3000); border:2px solid #FFD600; border-radius:12px; padding:18px; text-align:center; }
.rojo-card   { background: linear-gradient(135deg,#2a0000,#3d0000); border:2px solid #D50000; border-radius:12px; padding:18px; text-align:center; }
.card-text { font-size: 1.4rem; font-weight: 900; }
.card-sub  { font-size: 0.95rem; font-weight: 600; margin-top: 4px; }

.section-header { font-size: 1.1rem; font-weight: 700; color: #64ffda; text-transform: uppercase;
  letter-spacing: 2px; margin: 8px 0 4px 0; border-left: 3px solid #64ffda; padding-left: 10px; }
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════
#  HEADER GLOBAL
# ═══════════════════════════════════════════════════════
st.markdown("""
<div style="display:flex;align-items:center;gap:16px;padding:10px 0 20px 0;border-bottom:1px solid #1e3a5f;margin-bottom:20px;">
  <span style="font-size:2rem;">🏛️</span>
  <div>
    <div style="font-size:1.6rem;font-weight:900;color:#e6f1ff;line-height:1;">ANALISIS_BOLSA</div>
    <div style="font-size:0.85rem;color:#8892b0;letter-spacing:1px;">HQ Intelligence Terminal · Holding IA</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════
#  BARRA LATERAL / SIDEBAR GLOBAL
# ═══════════════════════════════════════════════════════
with st.sidebar:
    st.markdown('<div class="section-header">📖 Diccionario de Wall Street</div>', unsafe_allow_html=True)
    st.markdown("""
    **🟢 COMPRAR (Entradas)**: Acción rompiendo hacia arriba con mucha fuerza institucional.  
    **🔴 PELIGRO (Salidas)**: Acción muerta o cayendo libremente.  
    **Score %**: Calificación que el algoritmo le da (0 a 100). Sólo compra las mayores a 70.  
    
    ---
    **🛠️ EL MOTOR DE CORTO PLAZO (COHETES)**  
    **Alto Beta**: Empresas (Cripto, Tech, Ops) que se mueven o explotan rapidísimo.  
    **RSI (Termómetro)**: Si está entre 55 y 72, el "cohete" se está encendiendo (Buen momento para entrar).  
    **MACD**: Acelerador. Si es mayor a Cero, los compradores lideran.  
    **EMA 9/21**: Si la 9 está arriba, la tendencia de la semana es tu amiga.  
    
    ---
    **🛠️ EL MOTOR DE LARGO PLAZO (ACORAZADOS)**  
    **SMA 50/200**: El muro de concreto. Si el precio está por encime de su media de 200, la empresa es segura a largo plazo.  
    **PER (Valuación)**: Años que tardas en recuperar 1 dólar invirtiendo ciego. Mientras más bajo de 25, está más barata.  
    **Div Yield %**: Tu SUELDO anual gratis garantizado por ser dueño.  
    """)

# ═══════════════════════════════════════════════════════
#  PESTAÑAS PRINCIPALES
# ═══════════════════════════════════════════════════════
tab_hq, tab_swing, tab_value, tab_lupa, tab_div, tab_boveda, tab_bt = st.tabs([
    "🏠 HQ DASHBOARD",
    "⚡ SWING TRADING (Corto Plazo)",
    "🏦 VALUE INVESTING (Largo Plazo)",
    "🔍 ANÁLISIS INDIVIDUAL",
    "💵 DIVIDENDOS & RENTA PASIVA",
    "🗄️ BÓVEDA & PORTAFOLIO",
    "🤖 PILOTO AUTOMÁTICO",
])


# ══════════════════════════════════════════════
#  PESTAÑA 1: HQ DASHBOARD (Tipo de Cambio MXN)
# ══════════════════════════════════════════════
with tab_hq:
    st.markdown('<div class="section-header">Centro de Mando Ejecutivo</div>', unsafe_allow_html=True)

    # Botón de forzar actualización global del caché
    if st.button("🔄 Forzar Recarga de Todos los Datos", help="Borra el caché y recalcula todo desde cero (tarda ~15 seg)"):
        st.cache_data.clear()
        st.rerun()

    # Tipo de cambio cacheado
    usd_mxn = obtener_tipo_cambio()

    # SPY y BTC también cacheados (se extraen dentro de los screeners, reutilizamos)
    try:
        spy_fast  = yf.Ticker("SPY").fast_info
        spy_price = round(float(spy_fast['lastPrice']), 2)
        spy_var   = round((spy_price - float(spy_fast['previousClose'])) / float(spy_fast['previousClose']) * 100, 2)
    except:
        spy_price = 0; spy_var = 0

    try:
        btc_fast  = yf.Ticker("BTC-USD").fast_info
        btc_price = round(float(btc_fast['lastPrice']), 2)
        btc_var   = round((btc_price - float(btc_fast['previousClose'])) / float(btc_fast['previousClose']) * 100, 2)
    except:
        btc_price = 0; btc_var = 0

    c1, c2, c3, c4 = st.columns(4)
    for col, lbl, val, sub in [
        (c1, "USD → MXN (Live)", f"${usd_mxn}", "Tipo Cambio Banco"),
        (c2, "S&P 500 (SPY)", f"${spy_price}", f"{spy_var:+.2f}% hoy"),
        (c3, "Bitcoin (BTC)", f"${btc_price:,.0f}", f"{btc_var:+.2f}% hoy"),
        (c4, "Broker Activo", "GBM+", "Comisión: 0.25% + ISR 10%"),
    ]:
        with col:
            st.markdown(f"""<div class="hq-metric">
              <div class="label">{lbl}</div>
              <div class="value">{val}</div>
              <div class="sub">{sub}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Resumen de Portafolio en MXN ──
    df_hist = obtener_historial_df()
    if not df_hist.empty:
        st.markdown('<div class="section-header">Resumen de Portafolio en MXN</div>', unsafe_allow_html=True)
        with st.spinner("Calculando balances en pesos mexicanos..."):
            df_vivo = analizar_cartera_viva(df_hist)
        if not df_vivo.empty:
            def _to_mxn(row):
                if row['Moneda'] in ("USD", "N/A", ""):
                    return row['Invertido'] * usd_mxn
                return row['Invertido']
            def _net_mxn(row):
                if row['Moneda'] in ("USD", "N/A", ""):
                    return row['NETO_$'] * usd_mxn
                return row['NETO_$']
            tot_inv_mxn = df_vivo.apply(_to_mxn, axis=1).sum()
            tot_net_mxn = df_vivo.apply(_net_mxn, axis=1).sum()
            tot_cost     = df_vivo["Tax+GBM"].sum()

            r1, r2, r3, r4 = st.columns(4)
            for col, lbl, val, sub in [
                (r1, "Invertido Total MXN",  f"${tot_inv_mxn:,.2f}",  "Conversión en vivo"),
                (r2, "Utilidad Neta MXN",    f"${tot_net_mxn:,.2f}",  "Tras Tax + GBM"),
                (r3, "Costo Fiscal/Broker",  f"${tot_cost:,.2f}",     "0.5%GBM + 10%ISR"),
                (r4, "ROI Promedio",         f"{(tot_net_mxn/tot_inv_mxn*100 if tot_inv_mxn else 0):+.2f}%", "Sobre lo invertido"),
            ]:
                with col:
                    color_sub = "#64ffda" if "+" in sub else "#ff6b6b"
                    st.markdown(f"""<div class="hq-metric">
                      <div class="label">{lbl}</div><div class="value">{val}</div>
                      <div class="sub">{sub}</div></div>""", unsafe_allow_html=True)

            positions = df_vivo.groupby("Ticker")["Invertido"].sum().reset_index()
            fig_pie = px.pie(positions, names="Ticker", values="Invertido",
                             hole=0.55, title="Distribución de Cartera",
                             color_discrete_sequence=px.colors.sequential.Teal)
            fig_pie.update_layout(height=300, margin=dict(l=0,r=0,t=40,b=0),
                                  paper_bgcolor="rgba(0,0,0,0)", font_color="#e6f1ff")
            st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("Aún no tienes posiciones en la Bóveda. Usa la pestaña 🔍 para simular compras.")


# ══════════════════════════════════════════════
#  PESTAÑA 2: SWING TRADING
# ══════════════════════════════════════════════
with tab_swing:
    st.markdown('<div class="section-header">⚡ Modo Swing: Oportunidades de Corto Plazo (Días → Semanas)</div>', unsafe_allow_html=True)
    st.caption("Indicadores: EMA 9/21 (Cruce), MACD (Momentum), RSI (55-72 Momentum), Volumen Relativo")
    
    with st.expander("📖 Guía del Agente de Wall Street: ¿Cómo Operar en esta Pestaña?"):
        st.markdown("""
        **ESTRATEGIA:** Aquí el motor matemático escanea **ÚNICAMENTE** acciones de Alto Beta, Cripto y Tecnología. Busca **"El Cohete"** (Rompimiento de Momentum). No compramos cuando caen, compramos cuando explotan hacia arriba.
        
        *   🟢 **TABLA DE COMPRAS (Entradas)**: Estas son las **ÚNICAS** que debes comprar hoy. El algoritmo detectó fuerza institucional.
        *   🔴 **TABLA DE PELIGRO (Salidas)**: **NO COMPRES ESTAS ACCIONES**. Su tendencia está cayendo o muriendo. Si por error tienes alguna de esta tabla en tu Bóveda, debes considerar venderla ya.
        """)
        
    if st.button("🔄 Actualizar Radar Swing", key="btn_swing"):
        buscar_swing_trading.clear()
    with st.spinner("Ejecutando cazadores de Momentum de corto plazo..."):
        df_sw_buy, df_sw_sell = buscar_swing_trading()
    if not df_sw_buy.empty:
        st.subheader("🟢 TABLA MAESTRA DE COMPRAS (Alta Probabilidad Momentum)")
        st.dataframe(df_sw_buy, use_container_width=True, hide_index=True, height=380,
            column_config={
                "Ticker": st.column_config.TextColumn("Símbolo"),
                "Moneda": st.column_config.TextColumn("Divisa"),
                "Grafico_30d": st.column_config.LineChartColumn("Tendencia 30D"),
                "Score": st.column_config.ProgressColumn("Score", format="%d", min_value=0, max_value=100),
                "Precio": st.column_config.NumberColumn("Precio", format="%.2f"),
                "Variacion_%": st.column_config.NumberColumn("Var%", format="%+.2f%%"),
                "RSI_14": st.column_config.NumberColumn("RSI", format="%.1f"),
                "EMA9": st.column_config.NumberColumn("EMA9", format="%.2f"),
                "EMA21": st.column_config.NumberColumn("EMA21", format="%.2f"),
                "MACD": st.column_config.NumberColumn("MACD", format="%.4f"),
                "Vol_Relativo": st.column_config.NumberColumn("Vol.Rel.", format="%.1f"),
                "Stop_Loss": st.column_config.NumberColumn("Stop", format="%.2f"),
                "Accion": st.column_config.TextColumn("Veredicto"),
            })
        st.divider()
        st.subheader("🔴 TABLA DE PELIGRO (NO COMPRAR / Si tienes, LIQUIDA)")
        st.dataframe(df_sw_sell, use_container_width=True, hide_index=True, height=380,
            column_config={
                "Ticker": st.column_config.TextColumn("Símbolo"),
                "Moneda": st.column_config.TextColumn("Divisa"),
                "Grafico_30d": st.column_config.LineChartColumn("Caída 30D"),
                "Score": st.column_config.ProgressColumn("Score", format="%d", min_value=0, max_value=100),
                "Precio": st.column_config.NumberColumn("Precio", format="%.2f"),
                "Variacion_%": st.column_config.NumberColumn("Var%", format="%+.2f%%"),
                "RSI_14": st.column_config.NumberColumn("RSI", format="%.1f"),
                "Stop_Loss": st.column_config.NumberColumn("Stop", format="%.2f"),
                "Accion": st.column_config.TextColumn("Veredicto"),
            })
    else:
        st.error("Sin datos del Radar Swing.")


# ══════════════════════════════════════════════
#  PESTAÑA 3: VALUE INVESTING
# ══════════════════════════════════════════════
with tab_value:
    st.markdown('<div class="section-header">🏦 Modo Value: Oportunidades de Largo Plazo (Meses → Años)</div>', unsafe_allow_html=True)
    st.caption("Indicadores: SMA 50/200, PER (Valuación), Deuda/Capital, Dividendo")
    
    with st.expander("📖 Guía del Agente de Wall Street: ¿Cómo Operar en esta Pestaña?"):
        st.markdown("""
        **ESTRATEGIA:** Aquí el motor analiza **ACORAZADOS**. Empresas aburridas, gigantes y seguras que pagan dinero (Dividendos) solo por poseerlas (Energía, Finanzas, Consumo Básico).
        
        *   🟢 **TABLA DE ACUMULACIÓN**: Aquí te dice cuáles de estos gigantes están a precio de "Descuento Justo" según sus balances financieros. ¡Cómpralas y olvídate!
        *   🔴 **TABLA DE EVITAR**: Estas empresas están sobrevaloradas (Carísimas). **NO COMPRES**. Si ya tienes, el algoritmo te sugiere tomar ganancias.
        """)
        
    if st.button("🔄 Actualizar Radar Value", key="btn_value"):
        buscar_value_investing.clear()
    with st.spinner("Analizando balances financieros institucionales..."):
        df_v_buy, df_v_sell = buscar_value_investing()
    if not df_v_buy.empty:
        st.subheader("🟢 COMPRAR Y ACUMULAR (Precio de Descuento Institucional)")
        st.dataframe(df_v_buy, use_container_width=True, hide_index=True, height=380,
            column_config={
                "Ticker": st.column_config.TextColumn("Símbolo"),
                "Moneda": st.column_config.TextColumn("Divisa"),
                "Grafico_30d": st.column_config.LineChartColumn("Tendencia 30D"),
                "Score": st.column_config.ProgressColumn("Score", format="%d", min_value=0, max_value=100),
                "Precio": st.column_config.NumberColumn("Precio", format="%.2f"),
                "Variacion_%": st.column_config.NumberColumn("Var%", format="%+.2f%%"),
                "PER": st.column_config.TextColumn("PER"),
                "Dividendo_%": st.column_config.NumberColumn("Div %", format="%.2f%%"),
                "Deuda_Capital": st.column_config.TextColumn("Deuda/Kap"),
                "SMA_50": st.column_config.NumberColumn("SMA50", format="%.2f"),
                "SMA_200": st.column_config.NumberColumn("SMA200", format="%.2f"),
                "RSI_14": st.column_config.NumberColumn("RSI", format="%.1f"),
                "Stop_Loss": st.column_config.NumberColumn("Stop", format="%.2f"),
                "Accion": st.column_config.TextColumn("Veredicto"),
            })
        st.divider()
        st.subheader("🔴 TABLA DE PELIGRO (NO COMPRAR / TOMAR GANANCIAS)")
        st.dataframe(df_v_sell, use_container_width=True, hide_index=True, height=380,
            column_config={
                "Ticker": st.column_config.TextColumn("Símbolo"),
                "Moneda": st.column_config.TextColumn("Divisa"),
                "Grafico_30d": st.column_config.LineChartColumn("Caída 30D"),
                "Score": st.column_config.ProgressColumn("Score", format="%d", min_value=0, max_value=100),
                "Precio": st.column_config.NumberColumn("Precio", format="%.2f"),
                "PER": st.column_config.TextColumn("PER"),
                "Deuda_Capital": st.column_config.TextColumn("Deuda/Kap"),
                "Stop_Loss": st.column_config.NumberColumn("Stop", format="%.2f"),
                "Accion": st.column_config.TextColumn("Veredicto"),
            })
    else:
        st.error("Sin datos del Radar Value.")


# ══════════════════════════════════════════════
#  PESTAÑA 4: ANÁLISIS INDIVIDUAL (LUPA)
# ══════════════════════════════════════════════
with tab_lupa:
    modo_lupa = st.radio("Modo de Análisis:", ["⚡ Swing Trading (Corto)", "🏦 Value Investing (Largo)"], horizontal=True)
    ticker_input = st.text_input("Símbolo Bursátil (AAPL, BTC-USD, BIMBOA.MX):", value="").upper()

    if ticker_input:
        if "Swing" in modo_lupa:
            with st.spinner(f"Analizando Momentum de {ticker_input} (1ª vez ~5s, luego instantáneo)..."):
                resultado = analisis_individual_swing(ticker_input)  # Cacheado 60s
        else:
            with st.spinner(f"Radiografía Fundamental de {ticker_input} (1ª vez ~8s, luego instantáneo)..."):
                resultado = analisis_individual_value(ticker_input)  # Cacheado 60s

        if "error" in resultado:
            st.warning(f"No encontrado o datos insuficientes: {resultado['error']}")
        else:
            moneda = resultado.get("Moneda", "USD")
            score  = resultado.get("Score", 0)
            sem    = resultado.get("Semaforo", "")
            accion = resultado.get("Accion", "")

            # ── Barra de título del activo ──
            var_pct = resultado.get("Variacion_%", 0)
            delta_color = "normal" if var_pct >= 0 else "inverse"
            st.metric(f"💰 {resultado['Ticker']}", f"{resultado['Precio']} {moneda}", delta=f"{var_pct:+.2f}% hoy", delta_color=delta_color)
            st.divider()

            # ── Semáforo ──
            if "VERDE" in sem or "COMPRA" in sem:
                cls = "verde-card"
            elif "AMARILLO" in sem or "MANTENER" in sem or "ESPERAR" in sem:
                cls = "amarillo-card"
            else:
                cls = "rojo-card"
            st.markdown(f"""<div class="{cls}">
              <div class="card-text">{sem}</div>
              <div class="card-sub">{accion} | Score: {score}/100</div>
            </div><br>""", unsafe_allow_html=True)

            col_graf, col_dat = st.columns([2.5, 1])

            # ── Gráfica (con fallback a línea) ──
            with col_graf:
                st.subheader("Gráfica de Precio (6 Meses)")
                hist = None
                try:
                    from yahooquery import Ticker
                    t = Ticker(ticker_input)
                    hist = t.history(period="6mo")
                    if isinstance(hist.index, pd.MultiIndex):
                        hist = hist.xs(ticker_input, level='symbol')
                    hist = hist.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'})
                    if hasattr(hist.index, 'tz') and getattr(hist.index, 'tz', None) is not None:
                        hist.index = hist.index.tz_localize(None)
                except:
                    hist = None

                if hist is not None and not hist.empty:
                    fig = go.Figure()
                    # Intentar Candlestick; si el dataframe está limpio funciona
                    try:
                        fig.add_trace(go.Candlestick(
                            x=hist.index,
                            open=hist['Open'].astype(float),
                            high=hist['High'].astype(float),
                            low=hist['Low'].astype(float),
                            close=hist['Close'].astype(float),
                            name="Precio"
                        ))
                    except:
                        # Fallback: línea simple
                        fig.add_trace(go.Scatter(x=hist.index, y=hist['Close'].astype(float),
                                                  mode='lines', name='Precio', line=dict(color="#64ffda", width=2)))

                    fig.add_hline(y=resultado['Stop_Loss'], line_dash="dash", line_color="#ff6b6b",
                                  annotation_text="❌ Stop-Loss")
                    fig.add_hline(y=resultado['Target'],   line_dash="dash", line_color="#64ffda",
                                  annotation_text="🎯 Target 1:3")
                    if "SMA_200" in resultado and resultado["SMA_200"]:
                        fig.add_hline(y=resultado['SMA_200'], line_dash="dot", line_color="#8892b0",
                                      annotation_text="SMA 200")
                    if "SMA_50" in resultado and resultado["SMA_50"]:
                        fig.add_hline(y=resultado['SMA_50'], line_dash="dot", line_color="#ccd6f6",
                                      annotation_text="SMA 50")
                    fig.update_layout(xaxis_rangeslider_visible=False, height=470,
                                      margin=dict(l=0,r=0,t=10,b=0), template="plotly_dark",
                                      plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("No se pudo obtener el historial de precios para graficar.")

            # ── Panel de Datos ──
            with col_dat:
                st.subheader("El Dictamen")
                if "Swing" in modo_lupa:
                    st.metric("EMA9 / EMA21", f"{resultado.get('EMA9','N/A')} / {resultado.get('EMA21','N/A')}")
                    st.metric("MACD", f"{resultado.get('MACD','N/A')}")
                    st.metric("Volumen Relativo", f"{resultado.get('Vol_Relativo','N/A')}x")
                else:
                    st.metric("PER (Valuación)", f"{resultado.get('PER','N/A')}x")
                    st.metric("SMA 50 / 200", f"{resultado.get('SMA_50','N/A')} / {resultado.get('SMA_200','N/A')}")
                    st.metric("Dividendo Anual %", f"{resultado.get('Dividendo_%',0)}%")
                    st.metric("Deuda / Capital", f"{resultado.get('Deuda_Capital','N/A')}")
                st.metric("RSI (Oportunidad)", f"{resultado.get('RSI_14','N/A')}")
                st.metric("🚨 Stop-Loss", f"{resultado['Stop_Loss']} {moneda}")
                st.metric("🎯 Target (1:3)", f"{resultado['Target']} {moneda}")

                st.divider()
                st.caption("Calculadora de Ingreso Múltiple (Fracciones o Capital Libre)")
                
                # Fetch live exchange rate for calculation
                usd_mxn_live = obtener_tipo_cambio()
                
                modo_compra = st.radio(
                    "¿Cómo quieres dictar tu compra?",
                    ["🎯 Por Títulos", "💵 Presupuesto USD", "🇲🇽 Presupuesto MXN"],
                    horizontal=True
                )
                
                if modo_compra == "🎯 Por Títulos":
                    cantidad = st.number_input(f"Cantidad a Comprar ({ticker_input}):", min_value=0.001, value=1.0, step=0.001, format="%.3f")
                    monto_usd = round(cantidad * resultado['Precio'], 2)
                    monto_mxn = round(monto_usd * usd_mxn_live, 2)
                    st.caption(f"≈ Consumirá: **${monto_usd} USD** | (${monto_mxn} MXN)")
                
                elif modo_compra == "💵 Presupuesto USD":
                    monto_usd = st.number_input(f"Inversión Libre en USD:", min_value=1.0, value=100.0, step=10.0, format="%.2f")
                    cantidad = monto_usd / resultado['Precio']
                    monto_mxn = round(monto_usd * usd_mxn_live, 2)
                    st.caption(f"≈ Equivalente a comprar: **{cantidad:.4f}** acciones. (MXN extraído: ${monto_mxn})")
                
                else:
                    monto_mxn = st.number_input(f"Inversión Libre en Pesos MXN:", min_value=10.0, value=1000.0, step=100.0, format="%.2f")
                    monto_usd = monto_mxn / usd_mxn_live
                    cantidad = monto_usd / resultado['Precio']
                    st.caption(f"≈ Con ${monto_mxn} MXN envías **${monto_usd:.2f} USD** al bróker. Adquieres: **{cantidad:.4f}** acciones.")

                estrategia_compra = st.radio(
                    "Tipo de Operación:",
                    ["⚡ SWING (Corto Plazo)", "🏦 VALUE (Largo Plazo)"],
                    horizontal=True,
                    help="Swing = monitoréala de cerca y vende rápido. Value = guarda y cobra dividendos."
                )
                est_key = "SWING" if "SWING" in estrategia_compra else "VALUE"
                objetivo_pct = 10.0
                if est_key == "SWING":
                    objetivo_pct = st.slider(
                        "% de Ganancia Objetivo (Swing)", min_value=3, max_value=50, value=10, step=1,
                        help="Cuando el precio suba este % sobre tu costo, el sistema te grita \"VENDER\"."
                    )
                if st.button("💼 AÑADIR A BÓVEDA", type="primary", use_container_width=True):
                    registrar_operacion(ticker_input, "BUY", resultado["Precio"], cantidad,
                                        estrategia=est_key, objetivo_pct=float(objetivo_pct))
                    st.toast(f"✅ {cantidad} × {ticker_input} [{est_key}] registradas en Bóveda.")


# ══════════════════════════════════════════════
#  PESTAÑA 5: DIVIDENDOS
# ══════════════════════════════════════════════
with tab_div:
    st.markdown('<div class="section-header">💵 Radar de Renta Pasiva y Dividendos</div>', unsafe_allow_html=True)
    st.caption("Empresas que te pagan solo por ser propietario. El dinero cae en tu cuenta GBM+ sin clicks.")
    if st.button("🔄 Actualizar Pagadores de Dividendos"):
        pass
    with st.spinner("Escaneando frecuencias de pago, yields y próximas fechas ex-dividend..."):
        df_div = buscar_dividendos()
    if not df_div.empty:
        top_div = df_div.head(20)
        # Gráfica de Barras de Yield
        fig_bar = px.bar(top_div, x="Ticker", y="Yield_Anual_%", color="Yield_Anual_%",
                         title="Top Pagadores de Dividendos (% Anual)",
                         color_continuous_scale="Teal", text_auto=".2f")
        fig_bar.update_layout(height=320, template="plotly_dark",
                              paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_bar, use_container_width=True)

        st.dataframe(df_div, use_container_width=True, hide_index=True,
            column_config={
                "Ticker": st.column_config.TextColumn("Símbolo"),
                "Nombre": st.column_config.TextColumn("Empresa"),
                "Moneda": st.column_config.TextColumn("Divisa"),
                "Paga_Dividendos": st.column_config.TextColumn("Paga"),
                "Yield_Anual_%": st.column_config.NumberColumn("Yield % Anual", format="%.2f%%"),
                "Dividendo_x_Accion": st.column_config.NumberColumn("$/Acción", format="%.4f"),
                "Frecuencia": st.column_config.TextColumn("Frecuencia"),
                "Ex-Dividend_Date": st.column_config.TextColumn("Fecha Ex-Div."),
            })
    else:
        st.error("Error consultando los pagadores de dividendos.")


# ══════════════════════════════════════════════
#  PESTAÑA 6: BÓVEDA
# ══════════════════════════════════════════════
with tab_boveda:
    st.markdown('<div class="section-header">🗄️ Bóveda Institucional de Posiciones</div>', unsafe_allow_html=True)
    usd_mxn_bov = obtener_tipo_cambio()

    df_hist = obtener_historial_df()

    # ── Controles de Venta Parcial / Pánico ──
    col_v1, col_v2, col_v3 = st.columns(3)
    with col_v1:
        if not df_hist.empty:
            tickers_unicos = df_hist['ticker'].unique().tolist()
            t_sel = st.selectbox("Ticker a Vender:", tickers_unicos)
            quant_disponible = df_hist[df_hist['ticker'] == t_sel]['cantidad'].sum()
            st.caption(f"Tienes: {quant_disponible:.4f} unidades")
            q_vender = st.number_input("Cantidad a vender:", min_value=0.001,
                                       max_value=float(quant_disponible), value=float(quant_disponible),
                                       step=0.001, format="%.3f")
            if st.button("💸 VENDER PARCIAL / TOTAL", type="primary", use_container_width=True):
                vender_parcial(t_sel, q_vender)
                st.success(f"Vendidas {q_vender:.3f} unidades de {t_sel}.")
                st.rerun()
    with col_v3:
        if not df_hist.empty:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🔴 PÁNICO: Vaciar Toda la Bóveda", use_container_width=True):
                limpiar_boveda()
                st.success("Bóveda vaciada. Regresaste al punto cero.")
                st.rerun()

    st.divider()

    if df_hist.empty:
        st.info("⚠️ No hay posiciones activas. Usa la Lupa Individual para simular compras.")
    else:
        if st.button("🔄 EVALUAR CARTERA (Precios Vivos + Impuestos + Dividendos)", use_container_width=True):
            with st.spinner("Calculando posiciones, impuestos y dividendos..."):
                df_vivo = analizar_cartera_viva(df_hist)

            if not df_vivo.empty:
                # ── Totales ──
                tot_usd_inv     = df_vivo[df_vivo["Moneda"]=="USD"]["Invertido"].sum()
                tot_mxn_inv     = df_vivo[df_vivo["Moneda"]=="MXN"]["Invertido"].sum()
                tot_inv_mxn     = tot_usd_inv * float(usd_mxn_bov) + tot_mxn_inv
                tot_net_usd     = df_vivo[df_vivo["Moneda"]=="USD"]["NETO_$"].sum()
                tot_net_mxn_row = df_vivo[df_vivo["Moneda"]=="MXN"]["NETO_$"].sum()
                tot_net_mxn     = tot_net_usd * float(usd_mxn_bov) + tot_net_mxn_row
                roi_glob        = (tot_net_mxn / tot_inv_mxn * 100) if tot_inv_mxn else 0
                div_serie       = pd.to_numeric(df_vivo["Div_Anual_NETO"].replace("—", 0), errors='coerce').fillna(0)
                tot_div_neto    = div_serie.sum()
                alertas_swing   = df_vivo[df_vivo["Alerta"] == "🔔 ¡VENDER AHORA!"] if "Alerta" in df_vivo.columns else pd.DataFrame()

                # Alerta de Swing activa
                if not alertas_swing.empty:
                    tickers_alerta = ", ".join(alertas_swing["Ticker"].tolist())
                    st.error(f"🔔 ALERTA DE VENTA SWING: Los siguientes activos alcanzaron su objetivo de ganancia — **{tickers_alerta}**. Considera vender en GBM+ ahora.")

                m1, m2, m3, m4, m5 = st.columns(5)
                for col, lbl, val, sub in [
                    (m1, "Invertido Total (MXN)", f"${tot_inv_mxn:,.2f}", "USD + MXN convertido"),
                    (m2, "Utilidad Neta (MXN)",   f"${tot_net_mxn:,.2f}", "Después de Taxes"),
                    (m3, "Costo Fiscal Total",     f"${df_vivo['Tax+GBM'].sum():,.2f}", "GBM 0.5% + ISR 10%"),
                    (m4, "ROI Global",             f"{roi_glob:+.2f}%", "Sobre capital invertido"),
                    (m5, "💵 Renta Pasiva/Mes",   f"${tot_div_neto/12:,.2f}", f"Anual NETO: ${tot_div_neto:,.2f}"),
                ]:
                    with col:
                        st.markdown(f"""<div class="hq-metric">
                          <div class="label">{lbl}</div><div class="value">{val}</div>
                          <div class="sub">{sub}</div></div>""", unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)

                # ── Sub-pestañas Swing vs Value ──
                bov_swing, bov_value = st.tabs(["⚡ MIS POSICIONES SWING (Corto Plazo)", "🏦 MIS POSICIONES VALUE (Largo Plazo)"])

                COLS_SWING = {
                    "Ticker": st.column_config.TextColumn("Ticker"),
                    "Moneda": st.column_config.TextColumn("Divisa"),
                    "Cant": st.column_config.NumberColumn("Cant.", format="%.4f"),
                    "Costo_Base": st.column_config.NumberColumn("Mi Precio", format="%.4f"),
                    "Precio_Hoy": st.column_config.NumberColumn("Precio Hoy", format="%.4f"),
                    "Obj_%": st.column_config.TextColumn("🎯 Obj %", help="% de ganancia que fijaste al comprar"),
                    "Alerta": st.column_config.TextColumn("🔔 Estado", help="Si dice VENDER es que ya llegó al objetivo"),
                    "ROI_%": st.column_config.NumberColumn("ROI %", format="%+.2f%%"),
                    "NETO_$": st.column_config.NumberColumn("Cash Libre", format="%.2f"),
                    "Tax+GBM": st.column_config.NumberColumn("Impuestos", format="-%.2f"),
                    "IA_Dice": st.column_config.TextColumn("Robot:"),
                }

                COLS_VALUE = {
                    "Ticker": st.column_config.TextColumn("Ticker"),
                    "Moneda": st.column_config.TextColumn("Divisa"),
                    "Cant": st.column_config.NumberColumn("Cant.", format="%.4f"),
                    "Costo_Base": st.column_config.NumberColumn("Mi Precio", format="%.4f"),
                    "Precio_Hoy": st.column_config.NumberColumn("Precio Hoy", format="%.4f"),
                    "ROI_%": st.column_config.NumberColumn("ROI %", format="%+.2f%%"),
                    "NETO_$": st.column_config.NumberColumn("Cash Libre", format="%.2f"),
                    "Tax+GBM": st.column_config.NumberColumn("Impuestos", format="-%.2f"),
                    "Div_x_Pago": st.column_config.TextColumn("💵 Div/Pago"),
                    "Frecuencia_Pago": st.column_config.TextColumn("Frecuencia"),
                    "Div_Anual_NETO": st.column_config.TextColumn("Div Anual NETO"),
                    "IA_Dice": st.column_config.TextColumn("Robot:"),
                }

                with bov_swing:
                    df_s = df_vivo[df_vivo["Estrategia"] == "SWING"] if "Estrategia" in df_vivo.columns else df_vivo
                    if df_s.empty:
                        st.info("⚡ No tienes posiciones Swing activas. Compra una acción eligiendo modo Swing en la Lupa.")
                    else:
                        st.caption("🔔 El sistema grita VENDER cuando el precio actual supera tu objetivo. Monítora esta tabla a diario.")
                        st.dataframe(df_s, use_container_width=True, hide_index=True, column_config=COLS_SWING)

                with bov_value:
                    df_v = df_vivo[df_vivo["Estrategia"] == "VALUE"] if "Estrategia" in df_vivo.columns else df_vivo
                    if df_v.empty:
                        st.info("🏦 No tienes posiciones Value activas. Compra eligiendo modo Value en la Lupa.")
                    else:
                        st.caption("⏳ Estas posiciones son de largo plazo. Revisalas mensualmente. Aquí importan los dividendos y el PER.")
                        st.dataframe(df_v, use_container_width=True, hide_index=True, column_config=COLS_VALUE)


# ══════════════════════════════════════════════
#  PESTAÑA 7: PILOTO AUTOMÁTICO (ROBO-ADVISOR)
# ══════════════════════════════════════════════
with tab_bt:
    sub_bt_auto, sub_bt_man = st.tabs(["🤖 ROBO-ADVISOR (Portafolio Automático)", "🎯 SIMULADOR INDIVIDUAL (Elegir Acción)"])

    # ────────────────────────────────────────────────────────
    # 🤖 SUB-TAB 1: ROBO-ADVISOR
    # ────────────────────────────────────────────────────────
    with sub_bt_auto:
        st.markdown('<div class="section-header">🤖 Fondo IA en Piloto Automático</div>', unsafe_allow_html=True)
        st.write("Dame un capital y yo buscaré las mejores oportunidades del mundo HOY. Además, haré un `Backtesting` (viaje al pasado) para demostrarte cómo se hubiera comportado este mismo portafolio si el algoritmo lo hubiera estado administrando.")

        bt_c1, bt_c2 = st.columns([1, 2.5])

        with bt_c1:
            st.subheader("⚙️ Configuración del Fondo")
            fondo_mxn   = st.number_input("💵 Capital Disponible (MXN):", min_value=1000.0, value=10000.0, step=1000.0, help="El sistema dividirá este dinero en partes iguales.")
            perfil      = st.selectbox("Perfil de Riesgo:", [
                "Agresivo ⚡ (Puro Swing Trading)", 
                "Equilibrado ⚖️ (50% Swing / 50% Value)", 
                "Conservador 🏦 (Puro Value Investing)"
            ])
            bt_periodo  = st.selectbox("Máquina del Tiempo (Simulación):", ["1y", "2y", "3y"], index=1, help="Simular 1, 2 o 3 años hacia el pasado.")
            correr_auto = st.button("🚀 ARMAR Y SIMULAR PORTAFOLIO", type="primary", use_container_width=True)

        with bt_c2:
            if correr_auto:
                with st.spinner("Escaneando el mercado global para encontrar los mejores activos de hoy..."):
                    # Extraemos los mejores picks cacheados
                    df_swing_buy, _ = buscar_swing_trading()
                    df_value_buy, _ = buscar_value_investing()
                    
                    tickers_elegidos = []
                    # Seleccionar los Top 5 según el perfil
                    if "Agresivo" in perfil:
                        if not df_swing_buy.empty:
                            tickers_elegidos = df_swing_buy.head(5)["Ticker"].tolist()
                    elif "Conservador" in perfil:
                        if not df_value_buy.empty:
                            tickers_elegidos = df_value_buy.head(5)["Ticker"].tolist()
                    else:  # Equilibrado
                        t_sw  = df_swing_buy.head(3)["Ticker"].tolist() if not df_swing_buy.empty else []
                        t_val = df_value_buy.head(2)["Ticker"].tolist() if not df_value_buy.empty else []
                        tickers_elegidos = list(set(t_sw + t_val)) # set para evitar duplicados

                if not tickers_elegidos:
                    st.error("❌ El mercado está en condiciones adversas. El algoritmo no recomienda compras el día de hoy.")
                else:
                    st.success(f"**Selección Automática del Algoritmo:** {', '.join(tickers_elegidos)}")
                    
                    with st.spinner(f"Viajando {bt_periodo} al pasado para simular el Robot operando esta canasta de activos con tu capital de ${fondo_mxn:,.0f} MXN..."):
                        if "Agresivo" in perfil:
                            obj_p = 5.0
                            stp_p = 2.0
                            st.info("⚡ Estrategia de Wall Street [Alta Frecuencia]: Buscando ganancias rápidas del +5% cada pocos días / semanas con un Stop Loss muy ajustado (-2%). El interés compuesto hará su magia.")
                        elif "Conservador" in perfil:
                            obj_p = 15.0
                            stp_p = 8.0
                        else:
                            obj_p = 10.0
                            stp_p = 5.0

                        res = ejecutar_backtest_multiticker(tickers_elegidos, fondo_mxn, periodo=bt_periodo, objetivo_pct=obj_p, stop_pct=stp_p)

                    if res.get("error"):
                        st.error(f"❌ {res['error']}")
                    else:
                        roi       = res["ROI_%"]
                        color_r   = "#64ffda" if roi >= 0 else "#ff6b6b"

                        r1, r2, r3, r4 = st.columns(4)
                        for col, lbl, val, sub in [
                            (r1, "Capital Invertido", f"${fondo_mxn:,.0f} MXN", f"En {len(tickers_elegidos)} activos"),
                            (r2, "Capital Final", f"${res['Valor_Final']:,.2f} MXN", f"Después de {bt_periodo}"),
                            (r3, "Utilidad Neta", f"{res['Rendimiento_$']:+,.2f} MXN", f"Tras comisiones e ISR"),
                            (r4, "ROI Total (Rendimiento)", f"{roi:+.2f}%", f"Tasa de éxito: {res['Win_Rate_%']:.1f}%"),
                        ]:
                            with col:
                                st.markdown(f"""<div class="hq-metric">
                                  <div class="label">{lbl}</div>
                                  <div class="value" style="color:{color_r if 'Utilidad' in lbl or 'ROI' in lbl else '#e6f1ff'};">{val}</div>
                                  <div class="sub">{sub}</div>
                                </div>""", unsafe_allow_html=True)

                        st.markdown("<br>", unsafe_allow_html=True)

                        # ── Equity Curve ──
                        df_eq = res["df_equity"]
                        if not df_eq.empty:
                            fig_eq = go.Figure()
                            fig_eq.add_trace(go.Scatter(x=df_eq["Fecha"], y=df_eq["Valor_Portafolio"],
                                fill='tozeroy', mode='lines', line=dict(color="#64ffda", width=2),
                                fillcolor="rgba(100,255,218,0.08)", name="Valor del Fondo"))
                            fig_eq.add_hline(y=fondo_mxn, line_dash="dot", line_color="#8892b0",
                                             annotation_text=f"Capital Entregado: {fondo_mxn:,.0f} MXN")
                            
                            fig_eq.update_layout(title="📈 Comportamiento del Fondo Histórico (Backtesting Multi-Activo)",
                                height=350, template="plotly_dark",
                                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                                margin=dict(l=0,r=0,t=40,b=0))
                            st.plotly_chart(fig_eq, use_container_width=True)

                        # ── Botón de Aceptación ──
                        st.divider()
                        st.subheader("📥 Ejecutar en Tiempo Real")
                        st.write("¿El historial te convence? Presiona el botón para agregar **realmente** estas fracciones a tu Bóveda como si las compraras ahora:")
                        
                        if st.button("💼 ACEPTAR PROPUESTA E INVERTIR EN LA BÓVEDA", type="primary", use_container_width=True):
                            from cazador import obtener_tipo_cambio
                            usd_mxn_live = obtener_tipo_cambio()
                            presupuesto_por_accion_mxn = fondo_mxn / len(tickers_elegidos)
                            
                            for tk in tickers_elegidos:
                                try:
                                    t = yf.Ticker(tk)
                                    p_act = float(t.fast_info['lastPrice'])
                                    mon = str(t.fast_info.get('currency', 'USD'))
                                except:
                                    p_act = 1.0; mon = "USD"
                                
                                budget = presupuesto_por_accion_mxn
                                if mon == "USD":
                                    budget = budget / usd_mxn_live
                                cant = budget / p_act
                                
                                estr = "VALUE" if "Conservador" in perfil else "SWING"
                                registrar_operacion(tk, "BUY", p_act, cant, estrategia=estr)
                            
                            st.success("✅ ¡Hecho! Las operaciones han sido creadas. Ve a la pestaña de **BÓVEDA** para monitorear sus ganancias en tiempo real a partir de hoy.")

            else:
                st.info("👈 Ingresa tu capital, elige el perfil que más te guste y deja que la IA trabaje por ti.")

    # ────────────────────────────────────────────────────────
    # 🎯 SUB-TAB 2: SIMULADOR INDIVIDUAL (ELEGIR ACCIÓN)
    # ────────────────────────────────────────────────────────
    with sub_bt_man:
        st.markdown('<div class="section-header">🎯 Laboratorio de Simulación Individual</div>', unsafe_allow_html=True)
        st.caption("Escribe el nombre de un activo específico y simula en el pasado cuánto hubieras ganado operándolo con el algoritmo (Incluye cobro de dividendos).")
        
        c1_m, c2_m = st.columns([1, 2.5])
        
        with c1_m:
            st.subheader("⚙️ Parámetros Básicos")
            bt_ticker   = st.text_input("Ticker Específico:", value="AAPL", help="Ej: MSTR, NVDA, KO, BTC-USD").upper()
            bt_modo     = st.selectbox("Estrategia a simular:", ["SWING (Corto Plazo / Momentum)", "VALUE (Largo Plazo / Cruce SMA)"])
            bt_capital  = st.number_input("Capital Virtual Inicial:", min_value=100.0, value=10000.0, step=500.0, key="cap_man")
            bt_pct_t    = st.slider("¿Qué % de este fondo usa por compra?", 10, 100, 50, 5, key="pct_man")
            bt_periodo2 = st.selectbox("Máquina del Tiempo:", ["1y", "2y", "3y", "5y"], index=1, key="per_man")
            
            if "SWING" in bt_modo:
                st.caption("⚙️ Configuración Swing")
                bt_objetivo = st.slider("Objetivo Ganancia % (Toma Utilidad):", 3, 40, 10, 1, key="obj_m")
                bt_stop     = st.slider("Stop-Loss % (Corte de pérdida):", 2, 25, 5, 1, key="stp_m")
            else:
                bt_objetivo = 20.0
                bt_stop = 15.0
                
            correr_man = st.button("🚀 INICIAR SIMULACIÓN MANUAL", type="primary", use_container_width=True)
            
        with c2_m:
            if correr_man and bt_ticker:
                modo_str = "SWING" if "SWING" in bt_modo else "VALUE"
                with st.spinner(f"⏳ El Robot opera {bt_ticker} usando reglas {modo_str} en el pasado..."):
                    res = ejecutar_backtest(bt_ticker, bt_capital, float(bt_pct_t),
                                            bt_periodo2, float(bt_objetivo), float(bt_stop), modo=modo_str)

                if res.get("error"):
                    st.error(f"❌ {res['error']}")
                else:
                    moneda_bt = res["Moneda"]
                    roi       = res["ROI_%"]
                    color_r   = "#64ffda" if roi >= 0 else "#ff6b6b"

                    rm1, rm2, rm3, rm4 = st.columns(4)
                    for col, lbl, val, clr in [
                        (rm1, "Capital Virtual",   f"{bt_capital:,.0f}",          "#e6f1ff"),
                        (rm2, "Saldo Final",     f"{res['Valor_Final']:,.2f}",    color_r),
                        (rm3, f"Utilidad Neta ({moneda_bt})", f"{res['Rendimiento_$']:+,.2f}", color_r),
                        (rm4, "Retorno Histórico (ROI)",         f"{roi:+.2f}%",                  color_r),
                    ]:
                        with col:
                            st.markdown(f"""<div class="hq-metric">
                              <div class="label">{lbl}</div>
                              <div class="value" style="color:{clr};">{val}</div>
                            </div>""", unsafe_allow_html=True)

                    st.markdown("<br>", unsafe_allow_html=True)

                    # ── Equity Curve ──
                    df_eq  = res["df_equity"]
                    df_ops = res["df_operaciones"]
                    if not df_eq.empty:
                        fig_eq = go.Figure()
                        fig_eq.add_trace(go.Scatter(x=df_eq["Fecha"], y=df_eq["Valor_Total"],
                            fill='tozeroy', mode='lines', line=dict(color="#64ffda", width=2),
                            fillcolor="rgba(100,255,218,0.08)", name="Capital Acumulado"))
                        fig_eq.add_hline(y=bt_capital, line_dash="dot", line_color="#8892b0",
                                         annotation_text=f"Punto de Equilibrio: {bt_capital:,.0f}")
                        
                        if not df_ops.empty:
                            compras = df_ops[df_ops["Acción"].str.contains("COMPRA")]
                            ventas  = df_ops[df_ops["Acción"].str.contains("VENTA")]
                            divs    = df_ops[df_ops["Acción"].str.contains("COBRO DIVIDENDOS")]
                            if not compras.empty:
                                fig_eq.add_trace(go.Scatter(x=compras["Fecha"], y=compras["Capital_Libre"],
                                    mode='markers', marker=dict(color="#00C853", size=10, symbol="triangle-up"), name="🟢 Compra"))
                            if not ventas.empty:
                                fig_eq.add_trace(go.Scatter(x=ventas["Fecha"], y=ventas["Capital_Libre"],
                                    mode='markers', marker=dict(color="#ff6b6b", size=10, symbol="triangle-down"), name="🔴 Venta"))
                            if not divs.empty:
                                fig_eq.add_trace(go.Scatter(x=divs["Fecha"], y=divs["Capital_Libre"],
                                    mode='markers', marker=dict(color="#FFD600", size=10, symbol="star"), name="💵 Dividendo Recibido"))
                                    
                        fig_eq.update_layout(title=f"Evolución de Ganancias — {bt_ticker} ({bt_periodo2} | Modo {modo_str})",
                            height=380, template="plotly_dark",
                            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                            legend=dict(orientation="h", y=-0.2), margin=dict(l=0,r=0,t=40,b=0))
                        st.plotly_chart(fig_eq, use_container_width=True)

                    # ── Tabla de Operaciones ──
                    if not df_ops.empty:
                        with st.expander("Ver Auditoría (Registro de cada movimiento y cobro)"):
                            st.dataframe(df_ops, use_container_width=True, hide_index=True)
                    else:
                        st.warning("⚠️ Sin señales de compra válidas. El mercado no dio oportunidades en este periodo o debes cambiar la estrategia/ticker.")
            else:
                st.info("👈 Escribe tu ticket favorito y haz click en INICIAR SIMULACIÓN MANUAL.")

