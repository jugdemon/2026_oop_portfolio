from shiny import App, ui, render, reactive
import pandas as pd
import plotly.express as px
import plotly.io as pio
import os
import io
import requests
from abc import ABC, abstractmethod
from typing import Optional


class DataLoader(ABC):
    """Abstract base class for data loading strategies."""
    
    @abstractmethod
    def load(self) -> pd.DataFrame:
        """Load and return a DataFrame."""
        pass


class RemoteDataLoader(DataLoader):
    """Loads data from a remote URL."""
    
    def __init__(self, url: str, timeout: int = 10):
        self.url = url
        self.timeout = timeout
    
    def load(self) -> pd.DataFrame:
        """Fetch CSV data from remote URL."""
        try:
            resp = requests.get(self.url, timeout=self.timeout)
            resp.raise_for_status()
            return pd.read_csv(io.StringIO(resp.text))
        except Exception as e:
            raise IOError(f"Failed to load data from {self.url}: {e}")


class LocalDataLoader(DataLoader):
    """Loads data from a local CSV file."""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
    
    def load(self) -> pd.DataFrame:
        """Load CSV data from local file."""
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"Data file not found: {self.file_path}")
        return pd.read_csv(self.file_path)


class DataManager:
    """Manages data loading with fallback strategy."""
    
    def __init__(self, remote_url: Optional[str] = None, local_path: Optional[str] = None):
        self.remote_url = remote_url
        self.local_path = local_path or os.path.join(os.path.dirname(__file__), "data", "sample.csv")
        self._data: Optional[pd.DataFrame] = None
    
    def load(self) -> pd.DataFrame:
        """Load data with fallback from remote to local."""
        if self.remote_url:
            try:
                loader = RemoteDataLoader(self.remote_url)
                self._data = loader.load()
                return self._data
            except Exception:
                pass  # Fall back to local
        
        loader = LocalDataLoader(self.local_path)
        self._data = loader.load()
        return self._data
    
    @property
    def data(self) -> pd.DataFrame:
        """Get loaded data, loading if necessary."""
        if self._data is None:
            self.load()
        return self._data


class DataFilter:
    """Filters DataFrame based on column values."""
    
    def __init__(self, dataframe: pd.DataFrame):
        self.dataframe = dataframe
    
    def filter_by_column(self, column: str, value: str) -> pd.DataFrame:
        """Filter by column value, return all if value is 'All'."""
        if value == "All":
            return self.dataframe
        return self.dataframe[self.dataframe[column] == value]


class Visualizer:
    """Creates interactive visualizations."""
    
    def __init__(self, dataframe: pd.DataFrame):
        self.dataframe = dataframe
    
    def create_scatter_plot(self, x: str, y: str, color: str, title: str) -> str:
        """Create an interactive scatter plot and return HTML."""
        fig = px.scatter(
            self.dataframe,
            x=x,
            y=y,
            color=color,
            title=title,
            size="petal_width" if "petal_width" in self.dataframe.columns else None,
            hover_data=[col for col in self.dataframe.columns if col != color]
        )
        return pio.to_html(fig, include_plotlyjs='cdn')
    
    def create_data_table(self) -> str:
        """Create an HTML table from the DataFrame."""
        return self.dataframe.to_html()


class UIBuilder:
    """Builds the Shiny UI components."""
    
    def __init__(self, data_manager: DataManager):
        self.data_manager = data_manager
    
    def build_app_ui(self):
        """Build the main application UI."""
        df = self.data_manager.data
        species_choices = ["All"] + sorted(df["species"].unique().tolist())
        
        return ui.page_fluid(
            ui.h2("Sample Data Explorer"),
            ui.layout_sidebar(
                ui.sidebar(
                    ui.input_select(
                        "species",
                        "Species:",
                        choices=species_choices
                    ),
                ),
                ui.output_ui("table_ui"),
                ui.output_ui("scatter_plot")
            )
        )


class IrisApp:
    """Main application controller."""
    
    def __init__(self):
        # Initialize components
        self.data_manager = DataManager(
            remote_url=os.environ.get("POSIT_DATA_URL")
        )
        self.data_filter = DataFilter(self.data_manager.data)
        self.visualizer = Visualizer(self.data_manager.data)
        self.ui_builder = UIBuilder(self.data_manager)
    
    def build_ui(self):
        """Build and return the UI."""
        return self.ui_builder.build_app_ui()
    
    def build_server(self, input, output, session):
        """Build and return the server logic."""
        
        @reactive.Calc
        def filtered_data():
            """Filter data based on selected species."""
            return self.data_filter.filter_by_column("species", input.species())
        
        @output
        @render.ui
        def table_ui():
            """Render the data table."""
            d = filtered_data()
            table_html = Visualizer(d).create_data_table()
            return ui.tags.div(
                ui.h4(f"Showing {len(d)} rows"),
                ui.HTML(table_html)
            )
        
        @output
        @render.ui
        def scatter_plot():
            """Render the scatter plot."""
            d = filtered_data()
            viz = Visualizer(d)
            plot_html = viz.create_scatter_plot(
                x="sepal_length",
                y="petal_length",
                color="species",
                title="Sepal vs Petal Length"
            )
            return ui.HTML(plot_html)


# Initialize and run the app
iris_app = IrisApp()
app_ui = iris_app.build_ui()
server = iris_app.build_server

app = App(app_ui, server)
