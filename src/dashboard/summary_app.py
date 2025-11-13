#!/usr/bin/env python3
"""
Dash Dashboard: 13F-HR Summary Stats

Simple first page with:
- Dropdown to select issuer folder under `data/extracted_13F_HR`
- Dropdown to select period (yyyymmdd.xlsx) within issuer
- Loads the `InfoTable` sheet and displays:
  - All rows (paginated table)
  - Unique `issuer_name` count
  - Unique `class_title` count
  - Sum of `value_usd_quarter_end`
  - Unique `other_manager_seq` count
"""

from pathlib import Path
from typing import List, Tuple

import pandas as pd
from dash import Dash, dcc, html, Input, Output, dash_table
import plotly.graph_objects as go


DATA_ROOT = Path("data/extracted_13F_HR")

# Shared UI styles
BOX_STYLE = {
    "display": "grid",
    "gridTemplateColumns": "1fr 1fr",
    "gap": "12px",
    "border": "1px solid #ddd",
    "borderRadius": "8px",
    "padding": "12px",
    "backgroundColor": "rgba(255,255,255,0.0)",
}

# Use saved insights instead of raw stats wherever possible
try:
    from src.insights.summary import (
        load_summary_insights,
        period_label_from_filename as map_period_label,
        load_infotable,
        load_issuer_quarter_insights,
    )
except Exception:
    # Fallback imports if relative fail (when run as module)
    from insights.summary import (
        load_summary_insights,
        period_label_from_filename as map_period_label,
        load_infotable,
        load_issuer_quarter_insights,
    )


def list_issuers(base: Path = DATA_ROOT) -> List[str]:
    if not base.exists():
        return []
    return sorted([p.name for p in base.iterdir() if p.is_dir()])


def list_period_files(issuer: str, base: Path = DATA_ROOT) -> List[str]:
    d = base / issuer
    if not d.exists():
        return []
    return sorted([p.name for p in d.glob("*.xlsx")])


# load_infotable provided by insights.summary


def compute_stats(df: pd.DataFrame) -> Tuple[int, int, int, float, int]:
    # Kept for table-only fallback; insights are primary source.
    if df is None or df.empty:
        return 0, 0, 0, 0.0, 0
    val = pd.to_numeric(df.get("value_usd_quarter_end"), errors="coerce").fillna(0)
    rows = len(df)
    uniq_issuer = df.get("issuer_name").nunique(dropna=True) if "issuer_name" in df.columns else 0
    uniq_class = df.get("class_title").nunique(dropna=True) if "class_title" in df.columns else 0
    total_value = float(val.sum())
    uniq_other_mgr = df.get("other_manager_seq").nunique(dropna=True) if "other_manager_seq" in df.columns else 0
    return rows, uniq_issuer, uniq_class, total_value, uniq_other_mgr


def period_label_from_filename(filename: str) -> Tuple[str, Tuple[int, int]]:
    # Delegate to shared mapping in insights module
    return map_period_label(filename)

def quarter_color(quarter: int) -> str:
    # Selected Q1 -> orange; others -> gray
    return "#ffa500" if quarter == 1 else "#888888"


def build_app() -> Dash:
    app = Dash(__name__)
    issuers = list_issuers()

    app.layout = html.Div([
        html.H2("13F-HR Summary Dashboard"),
        html.Div([
            html.Label("Issuer"),
            dcc.Dropdown(
                id="issuer-dropdown",
                options=[{"label": i, "value": i} for i in issuers],
                value=issuers[0] if issuers else None,
                placeholder="Select issuer (folder under data/extracted_13F_HR)",
                clearable=False,
            ),
        ], style={"width": "30%", "display": "inline-block", "marginRight": "20px"}),
        html.Div([
            html.Label("Period"),
            dcc.Dropdown(id="period-dropdown", options=[], value=None, clearable=False),
        ], style={"width": "30%", "display": "inline-block"}),

        html.Hr(),
        html.Div(id="stats-bar", style={"display": "flex", "gap": "20px", "flexWrap": "wrap"}),

        html.Div([
            html.Div([
                html.Div([dcc.Graph(id="chart-unique-issuer")], style={"gridColumn": "1"}),
                html.Div(id="stats-unique-issuer", style={"gridColumn": "2"}),
            ], style=BOX_STYLE),
            html.Div([
                html.Div([dcc.Graph(id="chart-unique-class")], style={"gridColumn": "1"}),
                html.Div(id="stats-unique-class", style={"gridColumn": "2"}),
            ], style=BOX_STYLE),
            html.Div([
                html.Div([dcc.Graph(id="chart-sum-value")], style={"gridColumn": "1"}),
                html.Div(id="stats-sum-value", style={"gridColumn": "2"}),
            ], style=BOX_STYLE),
            html.Div([
                html.Div([dcc.Graph(id="chart-unique-other-mgr")], style={"gridColumn": "1"}),
                html.Div(id="stats-unique-other-mgr", style={"gridColumn": "2"}),
            ], style=BOX_STYLE),
        ], style={"display": "grid", "gridTemplateColumns": "repeat(2, minmax(300px, 1fr))", "gap": "16px"}),
    ])

    @app.callback(Output("period-dropdown", "options"), Output("period-dropdown", "value"), Input("issuer-dropdown", "value"))
    def update_periods(issuer_val):
        if not issuer_val:
            return [], None
        # Use issuer-level insights to build sorted period list
        issuer_quarters = load_issuer_quarter_insights(issuer_val).get("periods", [])
        # Sort by (year, quarter) desc
        issuer_quarters.sort(key=lambda x: (x.get("year", 0), x.get("quarter", 0)), reverse=True)
        opts = [{"label": iq.get("quarter_label", iq.get("period_filename", "")), "value": iq.get("period_filename", "")} for iq in issuer_quarters]
        default_val = issuer_quarters[0].get("period_filename") if issuer_quarters else None
        return opts, default_val

    @app.callback(
        Output("stats-bar", "children"),
        Output("chart-unique-issuer", "figure"),
        Output("stats-unique-issuer", "children"),
        Output("chart-unique-class", "figure"),
        Output("stats-unique-class", "children"),
        Output("chart-sum-value", "figure"),
        Output("stats-sum-value", "children"),
        Output("chart-unique-other-mgr", "figure"),
        Output("stats-unique-other-mgr", "children"),
        Input("issuer-dropdown", "value"),
        Input("period-dropdown", "value"),
    )
    def refresh_data(issuer_val, period_val):
        if not issuer_val or not period_val:
            empty_fig = go.Figure()
            empty_stats = html.Div([html.Small("No data")], style={"color": "#666"})
            return [], empty_fig, empty_stats, empty_fig, empty_stats, empty_fig, empty_stats, empty_fig, empty_stats
        # Load insights (auto-creates if missing)
        insight = load_summary_insights(issuer_val, period_val)
        metrics = insight.get("metrics", {})
        year = insight.get("year", 0)
        quarter = insight.get("quarter", 0)
        label = insight.get("quarter_label", "")

        rows = int(metrics.get("rows", 0))
        uniq_issuer = int(metrics.get("unique_issuer_name", 0))
        uniq_class = int(metrics.get("unique_class_title", 0))
        total_value = float(metrics.get("sum_value_usd_quarter_end", 0.0))
        uniq_other_mgr = int(metrics.get("unique_other_manager_seq", 0))
        # Stats cards
        cards = [
            html.Div([
                html.H4("Rows"), html.Div(str(rows))
            ], style={"border": "1px solid #ddd", "padding": "10px", "borderRadius": "6px", "minWidth": "150px"}),
            html.Div([
                html.H4("Unique issuer_name"), html.Div(str(uniq_issuer))
            ], style={"border": "1px solid #ddd", "padding": "10px", "borderRadius": "6px", "minWidth": "180px"}),
            html.Div([
                html.H4("Unique class_title"), html.Div(str(uniq_class))
            ], style={"border": "1px solid #ddd", "padding": "10px", "borderRadius": "6px", "minWidth": "180px"}),
            html.Div([
                html.H4("Sum value_usd_quarter_end"), html.Div(f"{total_value:,.0f}")
            ], style={"border": "1px solid #ddd", "padding": "10px", "borderRadius": "6px", "minWidth": "220px"}),
            html.Div([
                html.H4("Unique other_manager_seq"), html.Div(str(uniq_other_mgr))
            ], style={"border": "1px solid #ddd", "padding": "10px", "borderRadius": "6px", "minWidth": "220px"}),
        ]
        # Multi-quarter charts for last 5 quarters
        issuer_quarters = load_issuer_quarter_insights(issuer_val).get("periods", [])
        # Sort by (year, quarter) desc, then take top 5 and reverse to chronological order
        issuer_quarters.sort(key=lambda x: (x.get("year", 0), x.get("quarter", 0)), reverse=True)
        top5 = issuer_quarters[:5]
        top5 = list(reversed(top5))
        x_labels = [iq.get("quarter_label", iq.get("period_filename", "")) for iq in top5]
        # Color highlight for the selected period label
        selected_label = label
        colors = ["#8B0000" if lbl == selected_label else "#888888" for lbl in x_labels]

        y_unique_issuer = [iq.get("metrics", {}).get("unique_issuer_name", 0) for iq in top5]
        y_unique_class = [iq.get("metrics", {}).get("unique_class_title", 0) for iq in top5]
        y_sum_value = [iq.get("metrics", {}).get("sum_value_usd_quarter_end", 0.0) for iq in top5]
        y_unique_other_mgr = [iq.get("metrics", {}).get("unique_other_manager_seq", 0) for iq in top5]
        # Average value per holding (sum / rows)
        fig_unique_issuer = go.Figure([go.Bar(x=x_labels, y=y_unique_issuer, marker_color=colors)])
        fig_unique_class = go.Figure([go.Bar(x=x_labels, y=y_unique_class, marker_color=colors)])
        fig_sum_value = go.Figure([go.Bar(x=x_labels, y=y_sum_value, marker_color=colors)])
        fig_unique_other_mgr = go.Figure([go.Bar(x=x_labels, y=y_unique_other_mgr, marker_color=colors)])

        # Axis scaling (min*0.9 to max*1.1), concise titles, no y ticks/title, no x title
        def apply_axis(fig, y_values, title, is_count=False):
            if not y_values:
                mn, mx = 0, 1
            else:
                mn = min(y_values)
                mx = max(y_values)
                if mx == mn:
                    mx = mn + (1 if is_count else max(1.0, mn * 0.1))
            fig.update_layout(
                title=title,
                xaxis_title=None,
                yaxis_title=None,
                height=300,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                bargap=0.4,  # make bars thinner via larger gap
                bargroupgap=0.2,
            )
            fig.update_yaxes(range=[mn * 0.9, mx * 1.1], showticklabels=False)
            # Keep x ticks visible, drop y ticks; rely on default x ticks
            return fig

        fig_unique_issuer = apply_axis(fig_unique_issuer, y_unique_issuer, "Unique issuer_name", is_count=True)
        fig_unique_class = apply_axis(fig_unique_class, y_unique_class, "Unique class_title", is_count=True)
        fig_sum_value = apply_axis(fig_sum_value, y_sum_value, "Sum value_usd_quarter_end", is_count=False)
        fig_unique_other_mgr = apply_axis(fig_unique_other_mgr, y_unique_other_mgr, "Unique other_manager_seq", is_count=True)

        # Build per-chart stats (lowest, highest, selected quarter)
        def format_val(v, is_currency=False):
            if v is None:
                return "N/A"
            if is_currency:
                return f"{float(v):,.0f}"
            try:
                return f"{int(v):,}"
            except Exception:
                return str(v)

        def build_stats(y_vals, x_vals, selected, title, is_currency=False):
            if not y_vals:
                return html.Div([
                    html.H5(title, style={"margin": "0 0 8px"}),
                    html.Small("No data for selected issuer", style={"color": "#666"}),
                ])
            lowest = min(y_vals)
            highest = max(y_vals)
            try:
                sel_idx = x_vals.index(selected)
                sel_val = y_vals[sel_idx]
            except ValueError:
                sel_val = None
            return html.Div([
                html.H5(title, style={"margin": "0 0 8px"}),
                html.Div([
                    html.Div([html.Strong("Lowest:"), html.Span(f" {format_val(lowest, is_currency)}")]),
                    html.Div([html.Strong("Highest:"), html.Span(f" {format_val(highest, is_currency)}")]),
                    html.Div([html.Strong("Selected quarter:"), html.Span(f" {format_val(sel_val, is_currency)}")]),
                ], style={"display": "grid", "gridTemplateColumns": "1fr", "rowGap": "6px"}),
            ], style={"alignSelf": "center"})

        stats_unique_issuer = build_stats(y_unique_issuer, x_labels, selected_label, "Stats", is_currency=False)
        stats_unique_class = build_stats(y_unique_class, x_labels, selected_label, "Stats", is_currency=False)
        stats_sum_value = build_stats(y_sum_value, x_labels, selected_label, "Stats", is_currency=True)
        stats_unique_other_mgr = build_stats(y_unique_other_mgr, x_labels, selected_label, "Stats", is_currency=False)

        return (
            cards,
            fig_unique_issuer, stats_unique_issuer,
            fig_unique_class, stats_unique_class,
            fig_sum_value, stats_sum_value,
            fig_unique_other_mgr, stats_unique_other_mgr,
        )

    return app


if __name__ == "__main__":
    app = build_app()
    # Run local dev server
    app.run_server(host="127.0.0.1", port=8050, debug=True)