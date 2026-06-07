"""Balanzia Invest — copiloto de inversión (interfaz Streamlit).

Flujo principal (Recomendador):
  1) Eliges una de las 4 estrategias y un mercado (IBEX / EEUU / tu watchlist).
  2) Balanzia Invest escanea y te muestra las acciones recomendadas, rankeadas.
  3) Eliges una y ves su ficha: gráfico de velas + KPIs, recomendación de
     entrada/salida y los porqués (técnico + fundamental + analistas + noticias).

Pestañas adicionales: Diario de operaciones y Alertas.

Ejecutar:  streamlit run app.py

AVISO: herramienta de apoyo a la decisión, NO asesoramiento financiero.
Datos gratuitos de Yahoo con retardo (~15 min); el auto-refresco es "casi real".
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from embudo import alerts, analyzer, config, decision, journal, postmortem, watchlist
from embudo.data import catalog, health, realtime
from embudo.data import universe as universe_data
from embudo.profiles import PRESETS
from embudo.screener import recommender
from embudo.signals.horizons import Horizon

try:
    from streamlit_autorefresh import st_autorefresh
except Exception:  # dependencia opcional
    st_autorefresh = None

WATCHLIST_NAME = "⭐ Mi watchlist"
MARKETS = ["IBEX 35", "EEUU (Nasdaq 100 + Dow 30)", WATCHLIST_NAME]

st.set_page_config(page_title="Balanzia Invest · Copiloto de inversión", page_icon="📊", layout="wide")

LABEL_COLORS = {
    "Compra fuerte": "#0a8f3c", "Compra": "#4caf50", "Neutral": "#9e9e9e",
    "Venta": "#ef5350", "Venta fuerte": "#c62828",
}
DIM_NAMES = {"tecnico": "📈 Técnico", "fundamental": "🏛️ Fundamental",
             "analistas": "🧑‍💼 Analistas", "sentimiento": "📰 Noticias"}


# ----------------------------- utilidades ---------------------------------

def human_num(n) -> str:
    if n is None:
        return "—"
    try:
        n = float(n)
    except (TypeError, ValueError):
        return "—"
    for unit in ("", "K", "M", "B", "T"):
        if abs(n) < 1000:
            return f"{n:.1f}{unit}"
        n /= 1000
    return f"{n:.1f}P"


def _eur(ticker: str) -> bool:
    """Heurística de moneda: sufijos europeos (.MC, .DE, .PA…) = €; resto = $."""
    return "." in ticker and not ticker.upper().endswith((".US",))


def money(v, ticker: str) -> str:
    if v is None:
        return "—"
    return f"{v:.2f} €" if _eur(ticker) else f"${v:.2f}"


def money_big(v, ticker: str) -> str:
    if v is None:
        return "—"
    return f"{human_num(v)} €" if _eur(ticker) else f"${human_num(v)}"


def _default_finnhub_key() -> str:
    """Clave Finnhub: variable de entorno > secrets.toml > valor en config."""
    import os
    try:
        if "FINNHUB_KEY" in st.secrets:
            return str(st.secrets["FINNHUB_KEY"])
    except Exception:
        pass
    return os.getenv("FINNHUB_KEY") or config.FINNHUB_KEY


@st.cache_data(ttl=120, show_spinner=False)
def connectivity() -> bool:
    """¿Hay conexión a datos reales de Yahoo? (cacheado 2 min)."""
    return health.check_connectivity()


@st.cache_data(ttl=300, show_spinner=False)
def cached_analyze(ticker: str, strategy_name: str, capital: float, demo: bool):
    """Análisis cacheado 5 min para no rehacer el trabajo pesado en cada refresco.

    `demo` entra en la clave de caché para no mezclar datos reales y simulados.
    """
    return analyzer.analyze(ticker, PRESETS[strategy_name], capital=capital)


@st.cache_data(ttl=300, show_spinner=False)
def cached_screen(market: str, strategy_name: str, capital: float, demo: bool):
    profile = PRESETS[strategy_name]
    if market == WATCHLIST_NAME:
        return recommender.screen(watchlist.load(), profile, capital=capital), None
    return recommender.screen_named(market, profile, capital=capital)


# ----------------------------- barra lateral ------------------------------

def sidebar() -> dict:
    st.sidebar.header("⚙️ Configuración")
    strategy = st.sidebar.selectbox("Estrategia", list(PRESETS.keys()),
                                    help="Calidad/Valor (Buffett), seguir volumen, intraday o corto.")
    market = st.sidebar.selectbox("Mercado", MARKETS)
    capital = st.sidebar.number_input("Capital (€)", min_value=100.0, value=10_000.0, step=500.0)

    # Estado de conexión a datos reales.
    with st.sidebar:
        with st.spinner("Comprobando conexión a datos reales…"):
            online = connectivity()
    if online:
        st.sidebar.success("🟢 Conectado a **datos reales** (Yahoo Finance)")
    else:
        st.sidebar.error("🔴 Sin conexión a datos reales — se usará modo demo")

    # Modo demo: datos simulados. Por defecto OFF si hay internet; ON si no lo hay.
    demo = st.sidebar.checkbox("🧪 Modo demo (datos simulados)",
                               value=(config.DEMO_MODE or not online),
                               help="Datos NO reales. Útil sin internet o si las fuentes fallan.")
    config.DEMO_MODE = demo
    if demo:
        st.sidebar.info("Modo demo activo: datos simulados, no reales.")
    elif online:
        st.sidebar.caption("Datos reales con ~15 min de retardo (gratis). "
                           "Clave Finnhub abajo = cotización EEUU en tiempo real.")

    w = config.OBJECTIVE_WEIGHTS
    st.sidebar.caption(
        f"Análisis objetivo (igual en todas las estrategias) → "
        f"Téc {w['tecnico']*100:.0f}% · Fund {w['fundamental']*100:.0f}% · "
        f"Anal {w['analistas']*100:.0f}% · Notic {w['sentimiento']*100:.0f}%. "
        f"La estrategia solo decide largo/corto y el plan."
    )

    st.sidebar.markdown("---")
    st.sidebar.subheader("⏱️ Casi tiempo real")
    auto = st.sidebar.checkbox("Auto-refresco", value=False,
                               help="Datos gratis de Yahoo con ~15 min de retardo.")
    interval = st.sidebar.select_slider("Cada", options=[15, 30, 60, 120], value=30,
                                        format_func=lambda s: f"{s}s", disabled=not auto)
    finnhub_key = st.sidebar.text_input(
        "Clave Finnhub (tiempo real EEUU)", value=_default_finnhub_key(), type="password",
        help="Cotización EEUU en tiempo real. Se carga de .streamlit/secrets.toml o "
             "de la variable de entorno FINNHUB_KEY si existe.")
    if auto and st_autorefresh is not None:
        st_autorefresh(interval=interval * 1000, key="embudo_autorefresh")
    elif auto and st_autorefresh is None:
        st.sidebar.warning("Instala 'streamlit-autorefresh' para el refresco automático.")

    _sidebar_watchlist()
    st.sidebar.markdown("---")
    st.sidebar.warning("⚠️ Apoyo a la decisión, **no asesoramiento financiero**.")
    return {"strategy": strategy, "market": market, "capital": capital,
            "finnhub_key": finnhub_key.strip() or None, "demo": demo}


def _sidebar_watchlist() -> None:
    st.sidebar.markdown("---")
    st.sidebar.subheader("⭐ Mi watchlist")
    current = watchlist.load()

    # Autocompletar: escribe y sugiere tickers del catálogo (IBEX + EEUU).
    pick = st.sidebar.selectbox(
        "Añadir ticker (escribe para buscar)",
        options=[""] + catalog.suggestions(),
        format_func=lambda t: "— elige o escribe —" if t == "" else catalog.label(t),
        key="wl_pick",
    )
    custom = st.sidebar.text_input("…o escribe otro ticker", key="wl_add",
                                   placeholder="Ej.: NVDA, SAN.MC")
    if st.sidebar.button("Añadir", key="wl_add_btn"):
        chosen = (custom.strip() or pick).upper()
        if chosen:
            watchlist.add(chosen)
            st.rerun()
    if current:
        to_remove = st.sidebar.multiselect("Quitar", current, key="wl_rm")
        if to_remove:
            for t in to_remove:
                watchlist.remove(t)
            st.rerun()
        st.sidebar.caption("En lista: " + ", ".join(current))
    else:
        st.sidebar.caption("Aún no tienes valores guardados.")


# ----------------------------- componentes --------------------------------

def label_badge(label: str, score: float, confidence: float) -> None:
    color = LABEL_COLORS.get(label, "#9e9e9e")
    st.markdown(
        f"<div style='background:{color};color:white;padding:14px 18px;border-radius:10px;'>"
        f"<span style='font-size:1.4rem;font-weight:700'>{label}</span>"
        f"<span style='float:right'>score {score:+.2f} · confianza {confidence*100:.0f}%</span>"
        f"</div>",
        unsafe_allow_html=True,
    )


def render_regime(regime) -> None:
    if regime is None:
        return
    emoji = {"green": "🟢", "orange": "🟡", "red": "🔴"}.get(regime.color, "⚪")
    st.info(f"{emoji} **Régimen de mercado: {regime.label}** — {regime.detail}")


def kpi_header(a: analyzer.Analysis, finnhub_key: str | None):
    """Cabecera de KPIs con cotización casi-real. Devuelve la cotización en vivo."""
    f = a.fundamentals or {}
    quote = realtime.get_live_quote(a.ticker, finnhub_key)
    price = quote.price if quote.price is not None else a.last_price
    rel_vol = None
    if "rel_volume" in a.df and not a.df["rel_volume"].dropna().empty:
        rel_vol = float(a.df["rel_volume"].dropna().iloc[-1])

    cols = st.columns(6)
    cols[0].metric("Precio", money(price, a.ticker) if price else "—",
                   f"{quote.change_pct:+.2f}%" if quote.change_pct is not None else None)
    cols[1].metric("Cap. mercado", money_big(f.get("market_cap"), a.ticker))
    pe = f.get("trailing_pe") or f.get("forward_pe")
    cols[2].metric("PER", f"{pe:.1f}" if pe else "—")
    roe = f.get("roe")
    cols[3].metric("ROE", f"{roe*100:.0f}%" if roe is not None else "—")
    lo, hi = f.get("fifty_two_low"), f.get("fifty_two_high")
    sym = "€" if _eur(a.ticker) else "$"
    cols[4].metric("Rango 52s", f"{lo:.0f}-{hi:.0f} {sym}" if lo and hi else "—")
    cols[5].metric("Vol. vs media", f"{rel_vol:.1f}x" if rel_vol else "—")
    st.caption(f"🕒 {quote.asof} · fuente: {quote.source}"
               + ("  ·  ⏳ dato con retardo" if quote.delayed else "  ·  🟢 en vivo"))
    return quote


def price_chart(df: pd.DataFrame, name: str, levels=None, show_vwap: bool = False,
                live_price: float | None = None) -> go.Figure:
    # Última vela en tiempo real: actualiza el cierre (y mecha) del último día.
    if live_price is not None and not df.empty:
        df = df.copy()
        i = df.index[-1]
        df.loc[i, "Close"] = live_price
        df.loc[i, "High"] = max(df.loc[i, "High"], live_price)
        df.loc[i, "Low"] = min(df.loc[i, "Low"], live_price)
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.72, 0.28],
                        vertical_spacing=0.03)
    fig.add_trace(go.Candlestick(x=df.index, open=df["Open"], high=df["High"],
                                 low=df["Low"], close=df["Close"], name="Precio"), row=1, col=1)
    lines = [("sma_fast", "#1f77b4", "SMA50"), ("sma_slow", "#ff7f0e", "SMA200")]
    if show_vwap:
        lines.append(("vwap", "#9c27b0", "VWAP"))
    for col, color, label in lines:
        if col in df and df[col].notna().any():
            fig.add_trace(go.Scatter(x=df.index, y=df[col], line=dict(color=color, width=1),
                                     name=label), row=1, col=1)
    for lv in (levels or []):
        color = "#ef5350" if lv.kind == "resistencia" else "#26a69a"
        fig.add_hline(y=lv.price, line=dict(color=color, width=1, dash="dot"),
                      annotation_text=f"{lv.kind[:3]} {lv.price:.2f} ({lv.strength})",
                      annotation_position="right", annotation_font_size=9, row=1, col=1)
    colors = ["#26a69a" if c >= o else "#ef5350" for o, c in zip(df["Open"], df["Close"])]
    fig.add_trace(go.Bar(x=df.index, y=df["Volume"], marker_color=colors, name="Volumen"),
                  row=2, col=1)
    fig.update_layout(height=520, margin=dict(l=10, r=10, t=30, b=10),
                      xaxis_rangeslider_visible=False, showlegend=True, title=name)
    return fig


def _signal_table(signals) -> pd.DataFrame:
    return pd.DataFrame([
        {"Señal": s.name, "Lectura": "🟢" if s.score > 0 else "🔴" if s.score < 0 else "⚪",
         "Motivo": s.reason} for s in signals])


def _methodology_expander() -> None:
    w = config.OBJECTIVE_WEIGHTS
    with st.expander("📖 ¿Cómo se calcula? (metodología, sin magia)"):
        st.markdown(
            f"""
**Score objetivo** = media ponderada de 4 dimensiones, en el rango −1…+1 (mismo
cálculo para todas las estrategias):

- 📈 **Técnico {w['tecnico']*100:.0f}%** — tendencia (precio vs SMA50/200, ADX), momentum
  (MACD, RSI) y volumen (OBV, volumen relativo, divergencias) sobre datos diarios.
- 🏛️ **Fundamental {w['fundamental']*100:.0f}%** — calidad/valor estilo Buffett: ROE,
  deuda/equity, márgenes, PER frente a crecimiento.
- 🧑‍💼 **Analistas {w['analistas']*100:.0f}%** — consenso de Yahoo (1=compra fuerte … 5=venta).
- 📰 **Noticias {w['sentimiento']*100:.0f}%** — sentimiento de titulares (VADER).

**Etiqueta**: ≥0,50 Compra fuerte · 0,15…0,50 Compra · −0,15…0,15 Neutral ·
−0,50…−0,15 Venta · ≤−0,50 Venta fuerte.

**Confianza** = grado de acuerdo entre las 4 dimensiones (si se contradicen, baja
y se avisa). Si falta un dato (p. ej. sin analistas), esa dimensión pesa 0.

**La estrategia NO cambia este análisis.** Solo decide la dirección (largo/corto),
el plan de entrada/salida (stop por ATR o estructura, objetivo y R:R) y el backtest
de su señal. El régimen de mercado puede atenuar señales que reman contra la tendencia.

⚠️ Es apoyo a la decisión basado en datos públicos, **no asesoramiento financiero**.
"""
        )


def render_analysis(a: analyzer.Analysis, finnhub_key: str | None = None,
                    strategy_name: str = "") -> None:
    if a.error:
        st.error(a.error)
        return
    cons = a.consensus

    st.markdown(f"### {a.name}  ·  `{a.ticker}`")
    quote = kpi_header(a, finnhub_key)

    # ============ ANÁLISIS OBJETIVO (igual sea cual sea la estrategia) ============
    st.markdown("#### 📊 Análisis objetivo del valor")
    st.caption("Este análisis es el **mismo para cualquier estrategia**: valora el activo de "
               "forma objetiva. La estrategia solo decide, más abajo, si te encaja.")
    _methodology_expander()
    label_badge(cons.label, cons.score, cons.confidence)
    if cons.conflict:
        st.warning(cons.conflict)
    if cons.regime_note:
        st.caption(cons.regime_note)

    cols = st.columns(4)
    for col, (k, val) in zip(cols, cons.dimension_scores.items()):
        col.metric(DIM_NAMES.get(k, k), f"{val:+.2f}")

    live = quote.price if (quote and not config.DEMO_MODE) else None
    st.plotly_chart(price_chart(a.df, a.name, levels=a.levels, live_price=live),
                    use_container_width=True)
    if a.levels:
        st.caption("**Niveles automáticos:** " + " · ".join(
            f"{lv.kind} {lv.price:.2f} ({lv.strength})" for lv in a.levels))

    st.markdown("##### 🔍 Por qué (el razonamiento)")
    lcol, rcol = st.columns(2)
    with lcol:
        st.markdown("**📈 Técnico**")
        if cons.technical and cons.technical.signals:
            st.dataframe(_signal_table(cons.technical.signals), hide_index=True, use_container_width=True)
        else:
            st.caption("Sin señales técnicas.")
        st.markdown("**🏛️ Fundamental (calidad/valor)**")
        if cons.fundamental and cons.fundamental.group.signals:
            st.dataframe(_signal_table(cons.fundamental.group.signals), hide_index=True, use_container_width=True)
        else:
            st.caption(cons.fundamental.detail if cons.fundamental else "Sin datos fundamentales.")
    with rcol:
        st.markdown("**💬 Cualitativo**")
        if cons.analyst:
            st.write(f"🧑‍💼 **Analistas:** {cons.analyst.detail}")
        if cons.sentiment:
            st.write(f"📰 **Noticias:** {cons.sentiment.detail}")
            for h, s in cons.sentiment.headlines[:6]:
                emoji = "🟢" if s > 0.05 else "🔴" if s < -0.05 else "⚪"
                st.caption(f"{emoji} {h}")

    # ================= PARA TU ESTRATEGIA (depende de largo/corto) =================
    strat_dir = a.profile.direction
    p = a.trade_plan
    profit_pct = (p.reward_per_share / p.entry * 100) if (p and p.entry) else None
    rr = p.reward_risk if p else None

    st.markdown("---")
    st.markdown(f"#### 🎯 Para tu estrategia: **{strategy_name or a.profile.horizon.value}**")

    v = decision.decide(cons.score, strat_dir, profit_pct, rr, cons.confidence)
    bg = {"green": "#0a8f3c", "orange": "#e08e0b", "red": "#c62828"}[v.color]
    st.markdown(
        f"<div style='background:{bg};color:white;padding:16px 20px;border-radius:10px;margin-bottom:6px'>"
        f"<span style='font-size:1.5rem;font-weight:800'>{v.emoji} {v.action}</span>"
        f"<div style='font-size:1rem;margin-top:4px'>{v.phrase}</div></div>",
        unsafe_allow_html=True,
    )

    sentido = "🔻 CORTO (ganas si baja)" if strat_dir < 0 else "🔼 LARGO (ganas si sube)"
    st.markdown(f"**Plan de precio · {sentido}**")
    if p:
        cols = st.columns(6)
        cols[0].metric("Entrada", money(p.entry, a.ticker))
        cols[1].metric("Stop", money(p.stop, a.ticker))
        cols[2].metric("Objetivo", money(p.target, a.ticker))
        cols[3].metric("💰 Profit objetivo", f"+{profit_pct:.1f}%")
        cols[4].metric("R:R", f"{p.reward_risk:.1f}")
        cols[5].metric("Acciones", f"{p.shares}")
        st.caption(p.detail)
        if strat_dir < 0:
            st.caption("En corto: entras vendiendo a la *entrada*, el *stop* está por **encima** "
                       "(pérdida si sube) y el *objetivo* por **debajo** (beneficio si baja).")
    else:
        st.caption("Sin datos suficientes para el plan de entrada/salida.")

    if a.backtest and a.backtest.n_signals > 0:
        bt = a.backtest
        st.caption(f"🧪 Backtest de la señal de esta estrategia: acierto **{bt.win_rate*100:.0f}%** · "
                   f"retorno medio **{bt.avg_return*100:+.2f}%** ({bt.n_signals} señales).")
    elif a.backtest:
        st.caption("🧪 " + a.backtest.detail)

    if p and st.button("📓 Anotar este plan en el diario", key=f"jadd_{a.ticker}"):
        journal.add(journal.Trade(
            ticker=a.ticker, direction=p.direction, entry=p.entry, stop=p.stop,
            target=p.target, shares=p.shares, horizon=a.profile.horizon.value,
            thesis=f"{cons.label} (score {cons.score:+.2f}, conf {cons.confidence*100:.0f}%)"))
        st.success("Operación añadida al diario (pestaña 📓 Diario).")


# ----------------------------- pestañas -----------------------------------

def tab_recomendador(cfg: dict) -> None:
    st.subheader("🧭 Recomendador")
    st.caption(f"Estrategia: **{cfg['strategy']}** · Mercado: **{cfg['market']}**. "
               "Cambia ambos en la barra lateral.")

    if cfg["market"] == WATCHLIST_NAME and not watchlist.load():
        st.info("Tu watchlist está vacía. Añade valores desde la barra lateral ⭐.")
        return

    if st.button("🔎 Escanear / actualizar lista", type="primary"):
        cached_screen.clear()  # fuerza un re-escaneo fresco
        st.session_state["scanned"] = True

    if st.session_state.get("scanned"):
        with st.spinner("Escaneando mercado…"):
            df, regime = cached_screen(cfg["market"], cfg["strategy"], cfg["capital"], cfg["demo"])
        render_regime(regime)
        if df.empty:
            st.warning("Sin resultados. Puede ser falta de datos/conexión: activa el "
                       "**🧪 Modo demo** en la barra lateral o revisa tu internet.")
            return
        direction = PRESETS[cfg["strategy"]].direction
        accion = "compras" if direction > 0 else "ventas/cortos"
        st.success(f"Top candidatos ({accion}):")

        c1, c2 = st.columns([3, 2])
        orden = c1.radio("Ordenar por",
                         ["⭐ Mejor señal", "💰 Mayor profit estimado", "🏆 Calidad × profit"],
                         horizontal=True, key="orden")
        solo_claras = c2.checkbox("Solo señales claras (ocultar Neutral)", value=False, key="solo_claras")

        if solo_claras:
            df = df[df["label"] != "Neutral"].reset_index(drop=True)
        if df.empty:
            st.info("No hay señales claras ahora mismo con esta estrategia. Prueba otra o desactiva el filtro.")
            return

        # "Fuerza a favor" de la estrategia y métrica combinada calidad×profit.
        df = df.copy()
        df["_fuerza"] = df["score"] * direction
        df["_calidad_profit"] = df["_fuerza"].clip(lower=0) * df["confidence"] * df["profit_est"].fillna(0)
        if orden.startswith("💰"):
            df = df.sort_values("profit_est", ascending=False, na_position="last")
        elif orden.startswith("🏆"):
            df = df.sort_values("_calidad_profit", ascending=False)
        df = df.drop(columns=["_fuerza", "_calidad_profit"]).reset_index(drop=True)

        show = df.rename(columns={"ticker": "Ticker", "name": "Nombre", "label": "Señal",
                                  "score": "Score", "confidence": "Confianza",
                                  "profit_est": "Profit est. %", "rr": "R:R",
                                  "reason": "Motivo principal", "rel_volume": "Vol. rel."})
        st.dataframe(show, hide_index=True, use_container_width=True)
        st.download_button("⬇️ Exportar a CSV", df.to_csv(index=False).encode("utf-8"),
                           file_name=f"balanzia_{cfg['strategy'][:8]}.csv", mime="text/csv")

        st.markdown("---")
        tickers = df["ticker"].tolist()
        choice = st.selectbox("📄 Ver ficha de:", tickers, key="ficha_choice")
        if choice:
            with st.spinner(f"Analizando {choice}…"):
                a = cached_analyze(choice, cfg["strategy"], cfg["capital"], cfg["demo"])
            render_analysis(a, cfg["finnhub_key"], cfg["strategy"])

    st.markdown("---")
    with st.expander("🔬 Analizar otro valor por ticker"):
        manual = st.text_input("Ticker (Yahoo)", placeholder="AAPL, ITX.MC, SAN.MC…", key="manual_tk")
        if manual:
            with st.spinner(f"Analizando {manual}…"):
                a = cached_analyze(manual.strip().upper(), cfg["strategy"], cfg["capital"], cfg["demo"])
            render_analysis(a, cfg["finnhub_key"], cfg["strategy"])


def tab_diario() -> None:
    st.subheader("📓 Diario de operaciones")
    st.caption("Registra tus operaciones con su tesis y ciérralas para construir tu estadística real.")

    with st.expander("➕ Registrar operación manual"):
        c = st.columns(4)
        tk = c[0].text_input("Ticker", key="j_tk")
        direction = c[1].selectbox("Dirección", [1, -1],
                                   format_func=lambda d: "Largo" if d > 0 else "Corto", key="j_dir")
        entry = c[2].number_input("Entrada", min_value=0.0, value=100.0, key="j_entry")
        shares = c[3].number_input("Acciones", min_value=1, value=10, key="j_shares")
        c2 = st.columns(3)
        stop = c2[0].number_input("Stop", min_value=0.0, value=95.0, key="j_stop")
        target = c2[1].number_input("Objetivo", min_value=0.0, value=110.0, key="j_target")
        horizon = c2[2].selectbox("Horizonte", [h.value for h in Horizon], key="j_hz")
        thesis = st.text_input("Tesis (por qué entras)", key="j_thesis")
        if st.button("Guardar operación") and tk:
            journal.add(journal.Trade(tk.strip().upper(), int(direction), entry, stop, target,
                                      int(shares), horizon=horizon, thesis=thesis))
            st.success("Operación registrada.")
            st.rerun()

    open_t = journal.open_trades()
    st.markdown(f"#### Abiertas ({len(open_t)})")
    if open_t:
        for t in open_t:
            cols = st.columns([3, 2, 1.3, 1.3])
            sentido = "🟢 Largo" if t.direction > 0 else "🔴 Corto"
            cols[0].write(f"**{t.ticker}** {sentido} · entrada {t.entry:.2f} · stop {t.stop:.2f} · obj {t.target:.2f}")
            exit_p = cols[1].number_input("Cierre", min_value=0.0, value=float(t.entry), key=f"x_{t.id}")
            if cols[2].button("Cerrar", key=f"c_{t.id}"):
                journal.close(t.id, exit_p)
                st.rerun()
            if cols[3].button("Cerrar a precio actual", key=f"cl_{t.id}"):
                q = realtime.get_live_quote(t.ticker)
                if q.price:
                    journal.close(t.id, q.price, reason="precio en vivo")
                    st.rerun()
                else:
                    st.warning(f"No se pudo obtener el precio actual de {t.ticker}.")
            if t.thesis:
                cols[0].caption(f"Tesis: {t.thesis}")
    else:
        st.caption("No tienes operaciones abiertas.")

    closed_t = journal.closed_trades()
    st.markdown(f"#### Cerradas ({len(closed_t)})")
    if closed_t:
        rows = [{"Ticker": t.ticker, "Dir": "L" if t.direction > 0 else "C",
                 "Entrada": t.entry, "Salida": t.exit, "R": t.r_multiple(),
                 "P&L": t.pnl(), "P&L %": t.pnl_pct(),
                 "Plan": "✅" if t.followed_plan() else "⚠️"} for t in closed_t]
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

    _render_postmortem(journal.load())


def _render_postmortem(trades) -> None:
    st.markdown("---")
    st.subheader("🔬 Post-mortem (tu estadística)")
    s = postmortem.summarize(trades)
    if s.n == 0:
        st.info(s.lessons[0])
        return
    cols = st.columns(5)
    cols[0].metric("Operaciones", s.n)
    cols[1].metric("Acierto", f"{s.win_rate*100:.0f}%")
    cols[2].metric("Esperanza", f"{s.avg_r:+.2f}R")
    pf = "∞" if s.profit_factor == float("inf") else f"{s.profit_factor:.2f}"
    cols[3].metric("Profit factor", pf)
    cols[4].metric("P&L total", f"{s.total_pnl:+.0f} €")
    st.write("**Lecciones:**")
    for lesson in s.lessons:
        st.write(f"- {lesson}")
    if s.by_horizon:
        st.caption("R medio por horizonte: " + " · ".join(f"{h}: {r:+.2f}R" for h, r in s.by_horizon.items()))


def tab_alertas() -> None:
    st.subheader("🔔 Alertas")
    st.caption("Reglas comprobadas bajo demanda contra los datos actuales (sin coste, sin servicio en segundo plano).")

    with st.expander("➕ Crear alerta"):
        c = st.columns([2, 3, 2])
        tk = c[0].text_input("Ticker", key="a_tk")
        kind = c[1].selectbox("Condición", list(alerts.KINDS.keys()),
                              format_func=lambda k: alerts.KINDS[k], key="a_kind")
        value = c[2].number_input("Valor", value=100.0, key="a_val", disabled=kind.startswith("cross"))
        if st.button("Guardar alerta") and tk:
            alerts.add(alerts.AlertRule(tk.strip().upper(), kind, float(value)))
            st.success("Alerta creada.")
            st.rerun()

    rules = alerts.load()
    if not rules:
        st.caption("No tienes alertas. Crea una arriba.")
        return

    if st.button("🔍 Revisar alertas ahora", type="primary"):
        with st.spinner("Comprobando…"):
            hits = alerts.check_all(rules)
        fired = [h for h in hits if h.triggered]
        if fired:
            st.success(f"🔔 {len(fired)} alerta(s) activada(s):")
            for h in fired:
                st.write(f"- **{h.message}**")
        else:
            st.info("Ninguna alerta activada por ahora.")
        with st.expander("Ver estado de todas"):
            for h in hits:
                st.write(("🔔 " if h.triggered else "⚪ ") + h.message)

    st.markdown("#### Alertas configuradas")
    for r in rules:
        cols = st.columns([5, 1])
        cols[0].write(r.describe())
        if cols[1].button("🗑️", key=f"del_{r.id}"):
            alerts.remove(r.id)
            st.rerun()


def main() -> None:
    st.title("📊 Balanzia Invest — Copiloto de inversión")
    st.caption("IBEX + EEUU · técnico + fundamental (Buffett) + analistas + noticias · "
               "casi tiempo real · gratis y sin claves de pago.")
    cfg = sidebar()
    tabs = st.tabs(["🧭 Recomendador", "📓 Diario", "🔔 Alertas"])
    with tabs[0]:
        tab_recomendador(cfg)
    with tabs[1]:
        tab_diario()
    with tabs[2]:
        tab_alertas()


if __name__ == "__main__":
    main()
