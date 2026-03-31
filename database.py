import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import yfinance as yf
import sqlalchemy
from sqlalchemy import text

DB_NAME = "operaciones.db"

def get_connection():
    """
    Retorna una conexión activa. 
    Si detecta secretos de PostgreSQL (Supabase) en Streamlit Cloud, usa Postgres.
    De lo contrario, usa SQLite local.
    """
    if "connections" in st.secrets and "postgresql" in st.secrets.connections:
        # Modo Cloud: Supabase
        try:
            conn = st.connection("postgresql", type="sql")
            return conn, "POSTGRES"
        except Exception as e:
            st.error(f"Error conectando a Supabase: {e}")
            return None, "ERROR"
    else:
        # Modo Local: SQLite
        conn = sqlite3.connect(DB_NAME, check_same_thread=False)
        return conn, "SQLITE"

def init_db():
    conn, mode = get_connection()
    if mode == "SQLITE":
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            fecha TEXT NOT NULL,
            tipo TEXT NOT NULL,
            estrategia TEXT NOT NULL DEFAULT 'SWING',
            objetivo_pct REAL NOT NULL DEFAULT 10.0,
            precio_ejecucion REAL NOT NULL,
            cantidad REAL NOT NULL,
            monto_total REAL NOT NULL,
            precio_voo_referencia REAL
        )''')
        # Migración segura para SQLite
        for col, definition in [
            ("estrategia",   "TEXT NOT NULL DEFAULT 'SWING'"),
            ("objetivo_pct", "REAL NOT NULL DEFAULT 10.0"),
        ]:
            try:
                c.execute(f"ALTER TABLE trades ADD COLUMN {col} {definition}")
            except:
                pass
        conn.commit()
        conn.close()
    elif mode == "POSTGRES":
        # En Postgres las tablas se crean vía SQL Editor en el dashboard de Supabase (más seguro)
        # Pero aquí validamos que podamos leerla
        try:
            conn.query("SELECT 1 FROM trades LIMIT 1")
        except:
            st.warning("⚠️ La tabla 'trades' no existe en Supabase. Por favor ejecuta el script SQL proporcionado.")

def registrar_operacion(ticker: str, tipo: str, precio: float, cantidad: float,
                        estrategia: str = "SWING", objetivo_pct: float = 10.0):
    try:
        precio_voo = float(yf.Ticker("VOO").fast_info['lastPrice'])
    except:
        precio_voo = 0.0
        
    monto_total = precio * cantidad
    fecha_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    conn, mode = get_connection()
    
    if mode == "SQLITE":
        conn.execute(
            '''INSERT INTO trades 
               (ticker, fecha, tipo, estrategia, objetivo_pct, precio_ejecucion, cantidad, monto_total, precio_voo_referencia)
               VALUES (?,?,?,?,?,?,?,?,?)''',
            (ticker, fecha_str, tipo.upper(), estrategia.upper(), objetivo_pct, precio, cantidad, monto_total, precio_voo)
        )
        conn.commit()
        conn.close()
    elif mode == "POSTGRES":
        with conn.session as s:
            s.execute(
                text('''INSERT INTO trades 
                   (ticker, fecha, tipo, estrategia, objetivo_pct, precio_ejecucion, cantidad, monto_total, precio_voo_referencia)
                   VALUES (:t, :f, :tp, :est, :obj, :pr, :cant, :mt, :ref)'''),
                {"t": ticker, "f": fecha_str, "tp": tipo.upper(), "est": estrategia.upper(), 
                 "obj": objetivo_pct, "pr": precio, "cant": cantidad, "mt": monto_total, "ref": precio_voo}
            )
            s.commit()

def vender_parcial(ticker: str, cantidad_vender: float):
    conn, mode = get_connection()
    
    if mode == "SQLITE":
        c = conn.cursor()
        c.execute("SELECT id, cantidad FROM trades WHERE ticker=? ORDER BY fecha ASC", (ticker,))
        rows = c.fetchall()
        restante = cantidad_vender
        for row_id, row_cant in rows:
            if restante <= 0: break
            if row_cant <= restante:
                c.execute("DELETE FROM trades WHERE id=?", (row_id,))
                restante -= row_cant
            else:
                nueva_cant = row_cant - restante
                c.execute("UPDATE trades SET cantidad=?, monto_total=precio_ejecucion*? WHERE id=?",
                          (nueva_cant, nueva_cant, row_id))
                restante = 0
        conn.commit()
        conn.close()
    elif mode == "POSTGRES":
        # En Postgres usamos el motor de Streamlit Query
        df = conn.query(f"SELECT id, cantidad FROM trades WHERE ticker='{ticker}' ORDER BY fecha ASC")
        restante = cantidad_vender
        with conn.session as s:
            for idx, row in df.iterrows():
                if restante <= 0: break
                row_id = row['id']
                row_cant = row['cantidad']
                if row_cant <= restante:
                    s.execute(text("DELETE FROM trades WHERE id = :id"), {"id": row_id})
                    restante -= row_cant
                else:
                    nueva_cant = row_cant - restante
                    s.execute(text("UPDATE trades SET cantidad = :nc, monto_total = precio_ejecucion*:nc WHERE id = :id"),
                              {"nc": nueva_cant, "id": row_id})
                    restante = 0
            s.commit()

def obtener_historial_df() -> pd.DataFrame:
    conn, mode = get_connection()
    if mode == "SQLITE":
        df = pd.read_sql_query("SELECT * FROM trades", conn)
        conn.close()
        return df
    elif mode == "POSTGRES":
        return conn.query("SELECT * FROM trades")
    return pd.DataFrame()

def limpiar_boveda():
    conn, mode = get_connection()
    if mode == "SQLITE":
        conn.execute('DELETE FROM trades')
        conn.commit()
        conn.close()
    elif mode == "POSTGRES":
        with conn.session as s:
            s.execute(text("DELETE FROM trades"))
            s.commit()

def eliminar_operacion_por_ticker(ticker: str):
    conn, mode = get_connection()
    if mode == "SQLITE":
        conn.execute('DELETE FROM trades WHERE ticker = ?', (ticker,))
        conn.commit()
        conn.close()
    elif mode == "POSTGRES":
        with conn.session as s:
            s.execute(text("DELETE FROM trades WHERE ticker = :t"), {"t": ticker})
            s.commit()
