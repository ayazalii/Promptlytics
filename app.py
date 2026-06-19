"""
app.py
-------
Promptlytics — Natural Language to Dashboards
Gradio Blocks UI (the dark-SaaS rewrite seen in the project screenshots).

UI Layout (matching Figure 5.7 – 5.10 and the provided screenshots):
  ┌──────────────────────────────────────────────────┐
  │  NATURAL LANGUAGE QUERY   │  OPENAI API KEY      │
  │  [Textbox]                │  [Textbox, password] │
  ├────────────────────────────┬─────────────────────┤
  │  🚀 Generate Dashboard    │  ✕ Clear            │
  ├────────────────────────────┴─────────────────────┤
  │  Visualization | Insights | Generated SQL | Raw Data │
  │  [Plot]        [Markdown] [Code]         [DataFrame] │
  └──────────────────────────────────────────────────┘

Pipeline (on every "Generate Dashboard" click):
  1. If api_key provided  -> llm.generate_sql()
     Else                 -> intent_engine.classify() + sql_builder.build_sql()
  2. db.run_query(sql, params)
  3. visualizer.select_chart(df, intent, query)
  4. insights.generate(df, intent, query, engine_label)
"""

import gradio as gr

import db
import llm
import insights as insights_module
import visualizer
from nlp import intent_engine
import sql_builder

# ---------------------------------------------------------------------------
# Ensure the database exists on startup (seeded automatically by db.py)
# ---------------------------------------------------------------------------
db.get_connection()


# ---------------------------------------------------------------------------
# Core pipeline function
# ---------------------------------------------------------------------------
def generate_dashboard(nl_query: str, api_key: str):
    """
    End-to-end pipeline invoked by the Generate Dashboard button.

    Returns six values matched to the six Gradio output components:
        (plot, insights_md, sql_text, raw_df, error_md, sql_visible)
    """
    nl_query = (nl_query or "").strip()
    api_key = (api_key or "").strip()

    if not nl_query:
        empty_fig = visualizer._empty_figure("Enter a query above and click Generate Dashboard.")
        return empty_fig, "", "", None, gr.update(visible=False), gr.update(visible=False)

    # -----------------------------------------------------------------------
    # Step 1: NL -> SQL (rule-based OR OpenAI)
    # -----------------------------------------------------------------------
    sql = ""
    params = ()
    intent = {}
    engine_label = ""

    if api_key.startswith("sk-"):
        engine_label = "OpenAI GPT (gpt-3.5-turbo)"
        sql, intent, err = llm.generate_sql(nl_query, api_key)
        if err:
            err_fig = visualizer._empty_figure("⚠ API error — check the Insights tab.")
            return err_fig, f"**Error:** {err}", "", None, gr.update(visible=True), gr.update(visible=False)
    else:
        engine_label = "Rule-based engine (mock LLM)"
        intent = intent_engine.classify(nl_query)

        if intent["type"] == "UNSUPPORTED":
            err_fig = visualizer._empty_figure("⚠ Query not supported — see Insights tab.")
            return (
                err_fig,
                f"**Error:** {intent['error']}",
                "",
                None,
                gr.update(visible=True),
                gr.update(visible=False),
            )

        try:
            sql, params = sql_builder.build_sql(intent)
        except ValueError as exc:
            err_fig = visualizer._empty_figure("⚠ Could not build SQL — see Insights tab.")
            return err_fig, f"**Error:** {exc}", "", None, gr.update(visible=True), gr.update(visible=False)

    # -----------------------------------------------------------------------
    # Step 2: Execute SQL
    # -----------------------------------------------------------------------
    df, db_err = db.run_query(sql, params)
    if db_err:
        err_fig = visualizer._empty_figure("⚠ Database error — see Insights tab.")
        return err_fig, f"**Error:** {db_err}", sql, None, gr.update(visible=True), gr.update(visible=True)

    # -----------------------------------------------------------------------
    # Step 3: Visualization
    # -----------------------------------------------------------------------
    fig = visualizer.select_chart(df, intent, nl_query)

    # -----------------------------------------------------------------------
    # Step 4: Insights
    # -----------------------------------------------------------------------
    insights_md = insights_module.generate(df, intent, nl_query, engine_label)

    return (
        fig,                        # Visualization tab
        insights_md,                # Insights tab
        sql,                        # Generated SQL tab
        df if not df.empty else None,  # Raw Data tab
        gr.update(visible=False),   # error_banner (hidden on success)
        gr.update(visible=True),    # sql_code block (shown on success)
    )


# ---------------------------------------------------------------------------
# Custom CSS — reproduce the dark indigo palette from the screenshots
# ---------------------------------------------------------------------------
CUSTOM_CSS = """
body, .gradio-container {
    background-color: #0f1420 !important;
    color: #c7d2fe !important;
    font-family: 'Inter', 'Segoe UI', Arial, sans-serif !important;
}
/* Section labels */
.section-label {
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.1em;
    color: #6366f1;
    text-transform: uppercase;
    margin-bottom: 4px;
}
/* Input textboxes */
textarea, input[type="text"], input[type="password"] {
    background-color: #1a1f35 !important;
    border: 1px solid #2d3555 !important;
    border-radius: 10px !important;
    color: #e0e7ff !important;
    font-size: 15px !important;
    padding: 12px 16px !important;
}
textarea::placeholder, input::placeholder {
    color: #4b5280 !important;
}
/* Generate button */
.generate-btn {
    background: linear-gradient(135deg, #6366f1, #818cf8) !important;
    border: none !important;
    border-radius: 10px !important;
    color: #ffffff !important;
    font-size: 16px !important;
    font-weight: 700 !important;
    padding: 14px 0 !important;
    cursor: pointer !important;
    transition: opacity 0.2s;
}
.generate-btn:hover { opacity: 0.9 !important; }
/* Clear button */
.clear-btn {
    background-color: #1a1f35 !important;
    border: 1px solid #2d3555 !important;
    border-radius: 10px !important;
    color: #c7d2fe !important;
    font-size: 15px !important;
    padding: 14px 0 !important;
}
/* Tabs */
.tab-nav button {
    background: transparent !important;
    border-bottom: 2px solid transparent !important;
    color: #6b7280 !important;
    font-weight: 600 !important;
    padding: 10px 16px !important;
}
.tab-nav button.selected {
    border-bottom-color: #6366f1 !important;
    color: #c7d2fe !important;
}
/* Dataframe */
.dataframe { background-color: #1a1f35 !important; color: #c7d2fe !important; }
/* Error / info banners */
.error-banner { background-color: #2d1a1a; border-left: 4px solid #ef4444;
                padding: 12px 16px; border-radius: 8px; color: #fca5a5; }
"""


# ---------------------------------------------------------------------------
# Build the Gradio Blocks UI
# ---------------------------------------------------------------------------
def build_ui():
    with gr.Blocks(css=CUSTOM_CSS, title="Promptlytics — NL2Dashboards") as demo:

        # Header
        gr.HTML("""
        <div style="padding: 24px 0 8px 0;">
            <h1 style="color:#818cf8; font-size:28px; font-weight:800; margin:0;">
                📊 Promptlytics
            </h1>
            <p style="color:#6b7280; font-size:14px; margin:4px 0 0 0;">
                Natural Language to Dashboards &nbsp;·&nbsp; Rule-based NLP + Optional GPT
            </p>
        </div>
        """)

        # ── Input row ─────────────────────────────────────────────────────
        with gr.Row():
            with gr.Column(scale=3):
                gr.HTML('<div class="section-label">🔍 Natural Language Query</div>')
                query_box = gr.Textbox(
                    placeholder="e.g.  What is the monthly revenue trend?",
                    label="",
                    lines=3,
                    max_lines=5,
                )
            with gr.Column(scale=2):
                gr.HTML('<div class="section-label">🔑 OpenAI API Key</div>')
                key_box = gr.Textbox(
                    placeholder="sk-...  (leave blank to use mock LLM)",
                    label="",
                    lines=3,
                    max_lines=5,
                    type="password",
                )

        # ── Action buttons ────────────────────────────────────────────────
        with gr.Row():
            generate_btn = gr.Button("🚀  Generate Dashboard", elem_classes=["generate-btn"])
            clear_btn = gr.Button("✕  Clear", elem_classes=["clear-btn"])

        # ── Error banner (hidden by default) ─────────────────────────────
        error_banner = gr.Markdown(visible=False, elem_classes=["error-banner"])

        # ── Output tabs ───────────────────────────────────────────────────
        with gr.Tabs():
            with gr.Tab("📊 Visualization"):
                plot_output = gr.Plot(label="")

            with gr.Tab("💡 Insights"):
                insights_output = gr.Markdown()

            with gr.Tab("🔍 Generated SQL"):
                sql_output = gr.Code(language="sql", label="", visible=False)

            with gr.Tab("📋 Raw Data"):
                data_output = gr.DataFrame(label="", wrap=True)

        # ── Quick-example queries ─────────────────────────────────────────
        gr.HTML('<p style="color:#4b5280; font-size:12px; margin-top:24px;">Try:</p>')
        with gr.Row():
            for example in [
                "What is the monthly revenue trend?",
                "Show quantity sold by product",
                "Which region has the highest sales?",
                "How many sales records are there?",
                "Show revenue for the North region",
                "Top 3 products by total revenue",
            ]:
                gr.Button(example, size="sm").click(
                    fn=lambda q=example: q, outputs=query_box
                )

        # ── Wiring ────────────────────────────────────────────────────────
        generate_btn.click(
            fn=generate_dashboard,
            inputs=[query_box, key_box],
            outputs=[plot_output, insights_output, sql_output, data_output,
                     error_banner, sql_output],
        )

        clear_btn.click(
            fn=lambda: ("", "", gr.update(visible=False), "", None,
                        gr.update(visible=False), gr.update(visible=False)),
            outputs=[query_box, key_box, error_banner, insights_output,
                     data_output, plot_output, sql_output],
        )

    return demo


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    app = build_ui()
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True,
    )
