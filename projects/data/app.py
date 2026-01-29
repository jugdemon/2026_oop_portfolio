from shiny import App, ui, render, reactive
import pandas as pd
import plotly.express as px
import plotly.io as pio
import os
import io
import requests

# Try to load data from a Posit Cloud (or other) URL provided in the environment,
# otherwise fall back to the local sample CSV.
DATA_URL = os.environ.get("POSIT_DATA_URL")
LOCAL_PATH = os.path.join(os.path.dirname(__file__), "data", "sample.csv")

def load_data():
    if DATA_URL:
        try:
            resp = requests.get(DATA_URL, timeout=10)
            resp.raise_for_status()
            return pd.read_csv(io.StringIO(resp.text))
        except Exception:
            # Fall back to local CSV on any error
            pass
    return pd.read_csv(LOCAL_PATH)

df = load_data()

app_ui = ui.page_fluid(
    ui.h2("Sample Data Explorer"),
    ui.layout_sidebar(
        ui.sidebar(
            ui.input_select("species", "Species:", choices=["All"] + sorted(df["species"].unique().tolist())),
        ),
        ui.output_ui("table_ui"),
        ui.output_ui("scatter_plot")
    )
)

def server(input, output, session):

    @reactive.Calc
    def filtered():
        if input.species() == "All":
            return df
        return df[df["species"] == input.species()]

    @output
    @render.ui
    def table_ui():
        d = filtered()
        return ui.tags.div(
            ui.h4(f"Showing {len(d)} rows"),
            ui.HTML(d.to_html())
        )

    @output
    @render.ui
    def scatter_plot():
        d = filtered()
        fig = px.scatter(d, x="sepal_length", y="petal_length", color="species", title="Sepal vs Petal")
        return ui.HTML(pio.to_html(fig, include_plotlyjs='cdn'))

app = App(app_ui, server)
