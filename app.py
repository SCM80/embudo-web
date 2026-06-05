"""Embudo — copiloto de inversión (interfaz Streamlit).

Dos modos:
  • Explorar  -> el recomendador escanea un universo y rankea por estrategia.
  • Analizar  -> ficha completa de un valor con señales explicadas, riesgo y backtest.

Ejecutar:  streamlit run app.py

AVISO: herramienta de apoyo a la decisión, NO asesoramiento financiero.
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from embudo import analyzer, watchlist
from embudo.data import universe as universe_data
from embudo.profiles import PRESETS, StrategyProfile
from embudo.screener import recommender
from embudo.signals.horizons import Horizon

WATCHLIST_NAME = "⭐ Mi watchlist"

st.set_page_config(page_title="Embudo · Copiloto de inversión", page_icon="📊", layout="wide")

LABEL_COLORS = {
    "Compra fuerte": "#0a8f3c", "Compra": "#4caf50", "Neutral": "#9e9e9e",
    "Venta": "#ef5350", "Venta fuerte": "#c62828",
}


def sidebar_profile() -> tuple[str, StrategyProfile, float]:
    st.sidebar.header("⚙️ Estrategia")
    preset_name = st.sidebar.selectbox("Perfil", list(PRESETS.keys()))
    base = PRESETS[preset_name]

    horizon = st.sidebar.selectbox(
        "Horizonte", list(Horizon), index=list(Horizon).index(base.horizon),
        format_func=lambda h: h.value,
    )
    focus = st.sidebar.slider(
        "Enfoque  ·  0=Técnico  →  1=Cualitativo", 0.0, 1.0, base.focus, 0.05,
    )
    direction = -1 if horizon is Horizon.CORTO else 1
    min_rv = base.min_rel_volume if horizon is Horizon.INTRADAY else None
    profile = StrategyProfile(horizon=horizon, focus=focus, min_rel_volume=min_rv, direction=direction)

    capital = st.sidebar.number_input("Capital (€)", min_value=100.0, value=10_000.0, step=500.0)

    w = profile.weights
    st.sidebar.caption(
        f"Pesos → Técnico {w['tecnico']*100:.0f}% · "
        f"Analistas {w['analistas']*100:.0f}% · Sentimiento {w['sentimiento']*100:.0f}%"
    )
    return preset_name, profile, capital


def sidebar_watchlist() -> None:
    st.sidebar.markdown("---")
    st.sidebar.subheader("⭐ Mi watchlist")
    current = watchlist.load()
    new_t = st.sidebar.text_input("Añadir ticker", key="wl_add", placeholder="Ej.: NVDA")
    if st.sidebar.button("Añadir", key="wl_add_btn") and new_t:
        watchlist.add(new_t)
        st.rerun()
    if current:
        to_remove = st.sidebar.multiselect("Quitar de la lista", current, key="wl_rm")
        if to_remove:
            for t in to_remove:
                watchlist.remove(t)
            st.rerun()
        st.sidebar.caption("En lista: " + ", ".join(current))
    else:
        st.sidebar.caption("Aún no tienes valores guardados.")


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


def price_chart(df: pd.DataFrame, name: str, levels=None, show_vwap: bool = False) -> go.Figure:
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
    # Niveles de soporte (verde) y resistencia (rojo).
    for lv in (levels or []):
        color = "#ef5350" if lv.kind == "resistencia" else "#26a69a"
        fig.add_hline(y=lv.price, line=dict(color=color, width=1, dash="dot"),
                      annotation_text=f"{lv.kind[:3]} {lv.price:.2f} ({lv.strength})",
                      annotation_position="right", annotation_font_size=9, row=1, col=1)
    colors = ["#26a69a" if c >= o else "#ef5350" for o, c in zip(df["Open"], df["Close"])]
    fig.add_trace(go.Bar(x=df.index, y=df["Volume"], marker_color=colors, name="Volumen"),
                  row=2, col=1)
    fig.update_layout(height=520, margin=dict(l=10, r=10, t=30, b=10),
                      xaxis_rangeslider_visible=False, showlegend=True,
                      title=f"{name}")
    return fig


def render_analysis(a: analyzer.Analysis) -> None:
    if a.error:
        st.error(a.error)
        return
    cons = a.consensus
    c1, c2 = st.columns([2, 1])
    with c1:
        label_badge(cons.label, cons.score, cons.confidence)
        if cons.conflict:
            st.warning(cons.conflict)
        if cons.regime_note:
            st.caption(cons.regime_note)
    with c2:
        st.metric("Último precio", f"{a.last_price:.2f}" if a.last_price else "—")

    # Scores por dimensión.
    st.subheader("Desglose por dimensión")
    cols = st.columns(3)
    names = {"tecnico": "📈 Técnico", "analistas": "🧑‍💼 Analistas", "sentimiento": "📰 Sentimiento"}
    for col, (k, v) in zip(cols, cons.dimension_scores.items()):
        col.metric(names.get(k, k), f"{v:+.2f}")

    show_vwap = a.profile.horizon is Horizon.INTRADAY
    st.plotly_chart(price_chart(a.df, a.name, levels=a.levels, show_vwap=show_vwap),
                    use_container_width=True)

    if a.levels:
        st.caption("**Niveles automáticos:** " + " · ".join(
            f"{lv.kind} {lv.price:.2f} ({lv.strength})" for lv in a.levels))

    lcol, rcol = st.columns(2)
    with lcol:
        st.subheader("🔍 Señales técnicas (por qué)")
        if cons.technical and cons.technical.signals:
            rows = [{"Señal": s.name, "Lectura": "🟢" if s.score > 0 else "🔴" if s.score < 0 else "⚪",
                     "Motivo": s.reason} for s in cons.technical.signals]
            st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
        else:
            st.caption("Sin señales técnicas disponibles.")
    with rcol:
        st.subheader("💬 Capa cualitativa")
        if a.consensus.analyst:
            st.write(f"**Analistas:** {a.consensus.analyst.detail}")
        if a.consensus.sentiment:
            st.write(f"**Noticias:** {a.consensus.sentiment.detail}")
            for h, s in a.consensus.sentiment.headlines[:6]:
                emoji = "🟢" if s > 0.05 else "🔴" if s < -0.05 else "⚪"
                st.caption(f"{emoji} {h}")

    # Plan de riesgo + backtest.
    rcol1, rcol2 = st.columns(2)
    with rcol1:
        st.subheader("🎯 Plan de trade (riesgo)")
        if a.trade_plan:
            p = a.trade_plan
            st.dataframe(pd.DataFrame({
                "Concepto": ["Entrada", "Stop", "Objetivo", "R:R", "Acciones", "Capital en riesgo"],
                "Valor": [f"{p.entry:.2f}", f"{p.stop:.2f}", f"{p.target:.2f}",
                          f"{p.reward_risk:.1f}", f"{p.shares}", f"{p.capital_at_risk:.0f} €"],
            }), hide_index=True, use_container_width=True)
        else:
            st.caption("Sin datos suficientes para el plan de riesgo.")
    with rcol2:
        st.subheader("🧪 Backtest de la señal")
        if a.backtest and a.backtest.n_signals > 0:
            bt = a.backtest
            st.metric("Acierto histórico", f"{bt.win_rate*100:.0f}%",
                      help=f"{bt.n_signals} señales a {bt.horizon_bars} barras")
            st.metric("Retorno medio / operación", f"{bt.avg_return*100:+.2f}%")
            st.caption(bt.detail)
        else:
            st.caption(a.backtest.detail if a.backtest else "Backtest no disponible.")


def mode_explore(profile: StrategyProfile, capital: float) -> None:
    st.subheader("🧭 Explorar — recomendador por estrategia")
    options = list(universe_data.UNIVERSES.keys()) + [WATCHLIST_NAME]
    universe_name = st.selectbox("Universo", options)

    if universe_name == WATCHLIST_NAME:
        tickers = watchlist.load()
        if not tickers:
            st.info("Tu watchlist está vacía. Añade valores desde la barra lateral ⭐.")
            return
    else:
        tickers = universe_data.UNIVERSES[universe_name]
    st.caption(f"{len(tickers)} valores. Escanear puede tardar (datos gratuitos de Yahoo con rate-limit).")

    if st.button("🔎 Escanear universo", type="primary"):
        bar = st.progress(0.0, text="Iniciando…")

        def progress(i, total, ticker):
            bar.progress(i / total, text=f"Analizando {ticker} ({i}/{total})")

        if universe_name == WATCHLIST_NAME:
            df = recommender.screen(tickers, profile, capital=capital, progress=progress)
            regime = None
        else:
            df, regime = recommender.screen_named(universe_name, profile, capital=capital, progress=progress)
        bar.empty()
        render_regime(regime)
        if df.empty:
            st.warning("Ningún valor pasó los filtros (o sin datos). Prueba otro universo/perfil.")
            return
        accion = "compras" if profile.direction > 0 else "ventas/cortos"
        st.success(f"Top candidatos para **{profile.horizon.value}** ({accion}).")
        show = df.rename(columns={"ticker": "Ticker", "name": "Nombre", "label": "Señal",
                                  "score": "Score", "confidence": "Confianza",
                                  "reason": "Motivo principal", "rel_volume": "Vol. rel."})
        st.dataframe(show, hide_index=True, use_container_width=True)
        st.download_button("⬇️ Exportar a CSV", df.to_csv(index=False).encode("utf-8"),
                           file_name=f"embudo_{profile.horizon.name.lower()}.csv", mime="text/csv")
        st.session_state["last_screen"] = df["ticker"].tolist()


def mode_analyze(profile: StrategyProfile, capital: float) -> None:
    st.subheader("🔬 Analizar — ficha de un valor")
    default = st.session_state.get("last_screen", ["AAPL"])[0]
    ticker = st.text_input("Ticker (Yahoo)", value=default,
                           help="Ej.: AAPL, MSFT, ITX.MC (Inditex), SAN.MC (Santander)")
    if st.button("Analizar", type="primary") and ticker:
        with st.spinner(f"Analizando {ticker}…"):
            a = analyzer.analyze(ticker.strip().upper(), profile, capital=capital)
        render_analysis(a)


def main() -> None:
    st.title("📊 Embudo — Copiloto de inversión")
    st.caption("Análisis técnico + régimen de mercado + capa cualitativa + gestión de riesgo, "
               "con backtest. Gratis y sin API keys.")

    preset_name, profile, capital = sidebar_profile()
    sidebar_watchlist()
    st.sidebar.markdown("---")
    st.sidebar.warning("⚠️ Herramienta de apoyo a la decisión, **no asesoramiento financiero**.")

    tab_explore, tab_analyze = st.tabs(["🧭 Explorar (recomendador)", "🔬 Analizar (ficha)"])
    with tab_explore:
        mode_explore(profile, capital)
    with tab_analyze:
        mode_analyze(profile, capital)


if __name__ == "__main__":
    main()
