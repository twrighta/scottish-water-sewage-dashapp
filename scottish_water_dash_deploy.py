# Import packages
import pandas as pd
import numpy as np
from dash import Dash, html, dcc, callback
from dash.dependencies import Input, Output
import plotly_express as px
import dash_bootstrap_components as dbc
from datetime import date
import math
import gunicorn

# Read in csv as a pandas dataframe
#https://raw.githubusercontent.com/twrighta/scottish-water-sewage-dashapp/refs/heads/main/no_missing_scottish_sewage_spills.csv
df_path = 'https://raw.githubusercontent.com/twrighta/scottish-water-sewage-dashapp/main/no_missing_scottish_sewage_spills.csv'
df = pd.read_csv(df_path)

# Create lists of unique categories for dashboard filtering
ALL_ASSETS = list(np.unique(df["Asset Name"]))
ALL_YEARS = list(np.unique(df["Year"]))
ALL_SEASONS = list(np.unique(df["Season"]))
ALL_SOURCE_TYPES = list(np.unique(df["Source Type"]))
ALL_AREAS = list(np.unique(df["Area"]))
ALL_MONTHS = list(np.unique(df["Month"]))

# Append 'All...' to Years, Seasons, Areas, Months
ALL_YEARS.append("All")
ALL_MONTHS.append("All")
ALL_AREAS.append("All")
ALL_SEASONS.append("All")

SEASON_MONTH_DICT = {"Winter": ["November", "December", "January"],
                     "Spring": ["February", "March", "April"],
                     "Summer": ["May", "June", "July"],
                     "Autumn": ["August", "September", "October"]}

# Whole dataset metrics for metric text colour formatting
df_no_0 = df[
    (df["Duration Mins"] > 0) &
    (df["Volume Discharged"] > 0)
    ].copy()

AVG_DURATION_MINS = np.nanmean(df_no_0["Duration Mins"])
AVG_DISCHARGE = np.nanmean(df_no_0["Volume Discharged"])

# Other Global Formatting Variables
MARGIN_DICT = {"l": 10,
               "r": 10,
               "t": 30,
               "b": 10}
PLOT_STYLE = {"height": "90vh",
              "width": "90vh"}

# Instantiate Dashapp
app = Dash(__name__,
           suppress_callback_exceptions=True,
           external_stylesheets=[dbc.themes.FLATLY])
server = app.server

# Create the sidebar:
sidebar = html.Div([
    #  Options Header Section
    dbc.Row([
        html.H2("Filters and Options",
                style={"margin-top": "10px",
                       "margin-left": "10px",
                       "margin-right": "10px",
                       "border-radius": "10px",
                       "width": "95%"},
                className="bg-primary text-white font-italic")
    ],
        style={"height": "5vh",
               "fontWeight": "bold"}),

    # Filtering Dropdown Options Section
    dbc.Row([
        dbc.Col([
            html.P("Year",
                   style={"padding": "5px",
                          "font-weight": "bold"}),
            dcc.Dropdown(options=ALL_YEARS,
                         value=ALL_YEARS[0],
                         id="year-dropdown",
                         placeholder="Select Year",
                         style={"border-radius": "10px"}),
            html.P("Area",
                   style={"padding": "5px",
                          "font-weight": "bold"}),
            dcc.Dropdown(options=ALL_AREAS,
                         value=ALL_AREAS[0],
                         id="area-dropdown",
                         placeholder="Select Area",
                         style={"border-radius": "10px"})
        ]),
        dbc.Col([
            html.P("Season",
                   style={"padding": "5px",
                          "font-weight": "bold"}),
            dcc.Dropdown(
                options=[{"label": html.Span(["Winter"], style={"color": "blue"}),
                          "value": "Winter"},
                         {"label": html.Span(["Spring"], style={"color": "green"}),
                          "value": "Spring"},
                         {"label": html.Span(["Summer"], style={"color": "orange"}),
                          "value": "Summer"},
                         {"label": html.Span(["Autumn"], style={"color": "purple"}),
                          "value": "Autumn"},
                         {"label": html.Span(["All"], style={"color": "black"}),
                          "value": "All"}
                         ],
                value=ALL_SEASONS[0],
                id="season-dropdown",
                placeholder="Select Season",
                style={"border-radius": "10px"}),
            html.P("Month",
                   style={"padding": "5px",
                          "font-weight": "bold"}),
            dcc.Dropdown(options=ALL_MONTHS,
                         value=ALL_MONTHS[1],
                         id="month-dropdown",
                         placeholder="Select Month(s)",
                         style={"border-radius": "10px"})
        ])
    ],
        style={"height": "20vh"}),

    # DatePickerRange
    dbc.Row([
        dcc.DatePickerRange(
            start_date=date(2019, 1, 1),
            end_date=None,
            end_date_placeholder_text="End date",
            id="sidebar-date-picker-range",
            style={"width": "400"},
            clearable=True,
            minimum_nights=1,
            min_date_allowed=date(2019, 1, 1)
        )
    ],
        style={"height": "5vh",
               "justify-content": "space-around",
               "flex": "1",
               "border-radius": "10px"}),

    # Metrics Section
    dbc.Row([
        dbc.Col([
            html.H4("Number of Spills"),
            html.H5(id="sidebar-number-spills",
                    style={"font-weight": "bold"})
        ]),
        dbc.Col([
            html.H4("Average Duration (Mins)"),
            html.H5(id="sidebar-average-duration-mins",
                    style={"font-weight": "bold"})
        ]),
        dbc.Col([
            html.H4("Average Discharge (m3)"),
            html.H5(id="sidebar-average-discharge",
                    style={"font-weight": "bold"})
        ]),
        html.Hr()],
        style={"height": "30vh"}),

    # Pie chart of Volume Discharged by Source Type
    dbc.Row([
        dcc.Graph(id="sidebar-vol-pie",
                  style={"height": "30vh"})
    ],
        style={"height": "37.5vh"}),

    # Tom Credits
    dbc.Row([
        html.H4("by Tom Wright-Anderson",
                className="bg-primary text-white font-italic",
                style={"border-radius": "10px",
                       "width": "95%"})
    ],
        style={"fontWeight": "bold",
               "height": "2.5vh"})

])

# Content Section:
# Top Left: Plot of the Point Locations. Coloured by Source Type, Sized by Volume Discharged
# Top Right: Line/bar chart of Discharge (y) and Time (coloured by Source Type)
# Bottom Left: Asset stacked bar plot viewer. Select Number and Best/Worst filter.
# Bottom Right: 2 Plots: Horizontal Box Plots of Duration and Volume Discharged coloured by Source Type

content = html.Div([
    dbc.Row([
        dbc.Col([
            dcc.Graph(id="content-map-fig",
                      style={"height": "45vh",
                             "margins": MARGIN_DICT})
        ],
            width=6),
        dbc.Col([
            html.Div([
                dcc.Dropdown(options=["Overflow Event Start Time",
                                      "Start Minute",
                                      "Start Hour",
                                      "Week day"],
                             value="Overflow Event Start Time",
                             placeholder="Please select a timeframe",
                             id="timeframe-dropdown",
                             style={"border-radius": "10px",
                                    "width": "70%",
                                    "padding": "2px",
                                    "justify-content": "space-around"}),
                dcc.Graph(id="content-discharge-time-fig",
                          style={"height": "45vh"})
            ])
        ],
            width=6)
    ],
        style={"height": "50vh"}),

    # Lower Plots
    dbc.Row([
        dbc.Col([
            html.Div([
                dcc.RadioItems(id="discharge-duration-radio",
                               options=["Duration Mins", "Volume Discharged"],
                               value="Duration Mins",
                               inline=True,
                               labelStyle={"display": "inline-block",
                                           "padding": "10px"}
                               ),
                dcc.RadioItems(id="best-worst-radio",
                               options=["Best", "Worst"],
                               value="Worst",
                               inline=True,
                               labelStyle={"display": "inline-block",
                                           "padding": "10px"}
                               ),
                dcc.Input(id="assets-shown-input",
                          type="number",
                          value=3,
                          placeholder="Number of Assets",
                          step=1,
                          min=0,
                          style={"border-radius": "10px",
                                 "text-align": "center"})
            ]),
            html.Div([
                dcc.Graph(id="content-asset-performance-fig",
                          style={"height": "40vh",
                                 "margins": MARGIN_DICT})
            ])
        ],
            width=6),
        # Box Plots:
        dbc.Col([
            dbc.Col([
                html.Div([
                    dcc.RadioItems(options=["Duration Mins", "Volume Discharged"],
                                   value="Duration Mins",
                                   id="box-measure-radio",
                                   inline=True,
                                   labelStyle={"display": "inline-block",
                                               "padding": "10px"}),
                    dcc.Graph(id="content-box-fig",
                              style={"height": "45vh",
                                     "margin": MARGIN_DICT})],
                    style={"height": "45vh"})
            ])
        ],
            width=6)
    ],
        style={"height": "50vh"})

])

# Define the whole app layout within a single container containing a single row.
# The container/row contains 2 columns: a narrow sidebar (left), and a wide content box (right)
app.layout = dbc.Container([
    dbc.Row([
        dbc.Col(sidebar, width=3, className="bg-light"),
        # Sidebar, width 3
        dbc.Col(content, width=9, className="bg-light")
        # Content, width 9
    ])
],
    fluid=True,
    style={"height": "100vh"})


# Filtering dataframe helper function to call within callback functions
def filter_df(df, i_year, i_season, i_area, i_month, i_start_date, i_end_date):
    # if an end date is selected in the date picker
    if i_end_date is not None:
        df["Overflow Event Start Time"] = pd.to_datetime(df["Overflow Event Start Time"], errors='coerce')

        time_filtered_df = df.loc[
            df["Overflow Event Start Time"].between(pd.to_datetime(i_start_date), pd.to_datetime(i_end_date))
        ]

        # Initialize mask as True
        mask = pd.Series([True] * len(df))

        # No Month, Year or Season Filters
        filters_dict = {"Area": i_area}

        chosen_filters_dict = filters_dict.copy()

        for col, filter_value in filters_dict.items():
            if filter_value == "All":
                chosen_filters_dict.pop(col)

        # Iterate through filters_dict and apply conditions to mask
        for key, value in chosen_filters_dict.items():
            if value is not None:  # Apply filter only if value is not None
                mask &= time_filtered_df[key] == value

        # Apply mask to filter the DataFrame
        filtered_df = time_filtered_df[mask]

        # Filter further to where Volume discharged and Duration > 0
        filtered_df_final = filtered_df[
            (filtered_df["Volume Discharged"] > 0) &
            (filtered_df["Duration Mins"] > 0)
            ].copy()
        return filtered_df_final

    # If no end date is selected then do full filtering process
    if i_end_date is None:
        # Initialize mask as True
        mask = pd.Series([True] * len(df))

        filters_dict = {"Year": i_year,
                        "Season": i_season,
                        "Area": i_area,
                        "Month": i_month}

        chosen_filters_dict = filters_dict.copy()

        for col, filter_value in filters_dict.items():
            if filter_value == "All":
                chosen_filters_dict.pop(col)

        # Iterate through filters_dict and apply conditions to mask
        for key, value in chosen_filters_dict.items():
            if value is not None:  # Apply filter only if value is not None
                mask &= df[key] == value

        # Apply mask to filter the DataFrame
        filtered_df = df[mask]

        # Filter further to where Volume discharged and duration > 0
        filtered_df_final = filtered_df[
            (filtered_df["Volume Discharged"] > 0) &
            (filtered_df["Duration Mins"] > 0)
            ].copy()
        return filtered_df_final


# Define updating callbacks

#  Month dropdown if season selected
@callback(Output("month-dropdown", "options"),
          Input("season-dropdown", "value"))
def update_month_dropdown(i_season):
    if i_season != "All":
        options = SEASON_MONTH_DICT[i_season]
    if i_season == "All":
        options = ALL_MONTHS
    return options


# Calculate Metrics for Sidebar based on Filters
@app.callback([Output("sidebar-number-spills", "children"),
               Output("sidebar-average-duration-mins", "children"),
               Output("sidebar-average-discharge", "children"),
               Output("sidebar-average-duration-mins", "style"),
               Output("sidebar-average-discharge", "style")],
              Input("year-dropdown", "value"),
              Input("season-dropdown", "value"),
              Input("area-dropdown", "value"),
              Input("month-dropdown", "value"),
              Input("sidebar-date-picker-range", "start_date"),
              Input("sidebar-date-picker-range", "end_date")
              )
def update_sidebar_metrics(i_year, i_season, i_area, i_month, i_start_date, i_end_date):
    filtered_df = filter_df(df, i_year, i_season, i_area, i_month, i_start_date, i_end_date)

    if filtered_df.empty:
        num_spills = 0
        avg_duration = 0
        avg_discharge = 0
        avg_duration_color = None
        avg_discharge_color = None

    else:
        num_spills = str(len(filtered_df))
        avg_duration = str(round(np.mean(filtered_df["Duration Mins"]), 1))
        avg_discharge = str(round(np.mean(filtered_df["Volume Discharged"]), 1))

        avg_duration_float = round(np.mean(filtered_df["Duration Mins"]), 1)
        avg_discharge_float = round(np.mean(filtered_df["Volume Discharged"]), 1)

        duration_remainder = round(avg_duration_float - AVG_DURATION_MINS, 1)
        duration_remainder_str = '(+' + str(duration_remainder) + ')' if duration_remainder > 0 else '(' + str(
            duration_remainder) + ')'
        discharge_remainder = round(avg_discharge_float - AVG_DISCHARGE, 1)
        discharge_remainder_str = '(+' + str(discharge_remainder) + ')' if discharge_remainder > 0 else '(' + str(
            discharge_remainder) + ')'

        avg_duration = avg_duration + ' ' + duration_remainder_str
        avg_discharge = avg_discharge + ' ' + discharge_remainder_str

        # Colour text depending on its difference from whole dataset average
        if avg_duration_float < AVG_DURATION_MINS:
            avg_duration_color = {"color": "green"}
        else:
            avg_duration_color = {"color": "red"}

        if avg_discharge_float < AVG_DISCHARGE:
            avg_discharge_color = {"color": "green"}
        else:
            avg_discharge_color = {"color": "red"}

    return num_spills, avg_duration, avg_discharge, avg_duration_color, avg_discharge_color


# Update piechart of duration by source type
@app.callback(
    Output("sidebar-vol-pie", "figure"),
    [Input("year-dropdown", "value"),
     Input("season-dropdown", "value"),
     Input("area-dropdown", "value"),
     Input("month-dropdown", "value"),
     Input("sidebar-date-picker-range", "start_date"),
     Input("sidebar-date-picker-range", "end_date")
     ])
def update_sidebar_pie(i_year, i_season, i_area, i_month, i_start_date, i_end_date):
    filtered_df = filter_df(df, i_year, i_season, i_area, i_month, i_start_date, i_end_date)

    if filtered_df.empty:
        empty_fig = px.pie(names=["No Data"],
                           values=[1],
                           title="Please reselect your filters (e.g., Date range)",
                           template="seaborn")
        empty_fig.update_layout(margin=MARGIN_DICT,
                                plot_bgcolor='rgba(0, 0, 0, 0)',
                                paper_bgcolor='rgba(0, 0, 0, 0)')
        return empty_fig

    pie_fig = px.pie(data_frame=filtered_df,
                     names="Source Type",
                     values="Duration Mins",
                     color="Source Type",
                     template="seaborn",
                     title=f"<b>Sewage Overflow Duration by Source Type</b>")

    pie_fig.update_layout(margin=MARGIN_DICT,
                          plot_bgcolor='rgba(0, 0, 0, 0)',
                          paper_bgcolor='rgba(0, 0, 0, 0)'
                          )

    return pie_fig


# Update a map plot of filtered locations, sized points by Volume Discharge and Coloured by Source Type
@callback(
    Output("content-map-fig", "figure"),
    [Input("year-dropdown", "value"),
     Input("season-dropdown", "value"),
     Input("area-dropdown", "value"),
     Input("month-dropdown", "value"),
     Input("sidebar-date-picker-range", "start_date"),
     Input("sidebar-date-picker-range", "end_date")])
def update_content_map(i_year, i_season, i_area, i_month, i_start_date, i_end_date):
    filtered_df = filter_df(df, i_year, i_season, i_area, i_month, i_start_date, i_end_date)

    filtered_df = filtered_df[["Asset Name", "Year", "Source Type", "Latitude", "Longitude", "Volume Discharged"]]

    if filtered_df.empty:
        empty_fig = px.pie(names=["No Data"],
                           values=[1],
                           title="Please reselect your filters (e.g., Date range)",
                           template="seaborn")
        empty_fig.update_layout(margin=MARGIN_DICT,
                                plot_bgcolor='rgba(0, 0, 0, 0)',  # transparent plot area
                                paper_bgcolor='rgba(0, 0, 0, 0)')
        return empty_fig

    filtered_df = filtered_df.groupby(by=["Asset Name", "Year", "Source Type", "Latitude", "Longitude"],
                                      as_index=False).sum()
    num_sources_str = str(len(np.unique(filtered_df["Asset Name"])))
    map_fig = px.scatter_map(filtered_df,
                             lat="Latitude",
                             lon="Longitude",
                             color="Source Type",
                             size="Volume Discharged",
                             size_max=50,
                             zoom=7,
                             template="seaborn",
                             hover_name="Asset Name",
                             title=f"<b>Sewage Overflow Sources: {num_sources_str}<b>",
                             center={"lat": 56.24936914381658,
                                     "lon": -3.8824581054934506})
    map_fig.update_layout(margin=MARGIN_DICT,
                          plot_bgcolor='rgba(0, 0, 0, 0)',  # transparent plot area
                          paper_bgcolor='rgba(0, 0, 0, 0)',
                          title={
                              'xanchor': 'center',
                              'yanchor': 'top'},
                          showlegend=False)

    return map_fig


# Update line/bar chart of Discharge and Time, coloured by Source Type
@callback(
    Output("content-discharge-time-fig", "figure"),
    [Input("year-dropdown", "value"),
     Input("season-dropdown", "value"),
     Input("area-dropdown", "value"),
     Input("month-dropdown", "value"),
     Input("timeframe-dropdown", "value"),
     Input("sidebar-date-picker-range", "start_date"),
     Input("sidebar-date-picker-range", "end_date")])
def update_content_discharge_time(i_year, i_season, i_area, i_month, i_time_frame, i_start_date, i_end_date):
    filtered_df = filter_df(df, i_year, i_season, i_area, i_month, i_start_date, i_end_date)

    if filtered_df.empty:
        empty_fig = px.pie(names=["No Data"],
                           values=[1],
                           title="Please reselect your filters (e.g., Date range)",
                           template="seaborn")
        empty_fig.update_layout(margin=MARGIN_DICT,
                                plot_bgcolor='rgba(0, 0, 0, 0)',
                                paper_bgcolor='rgba(0, 0, 0, 0)')
        return empty_fig

    filtered_df = filtered_df[[i_time_frame, "Volume Discharged", "Source Type"]]

    # Line Charts
    if i_time_frame == "Overflow Event Start Time":
        line_fig = px.line(data_frame=filtered_df.sort_values(by=i_time_frame, ascending=True),
                           x=i_time_frame,
                           y="Volume Discharged",
                           color="Source Type",
                           line_group="Source Type",
                           title=f"<b>Volume Discharged over time<b>",
                           template="seaborn")
        line_fig.update_layout(margin=MARGIN_DICT,
                               plot_bgcolor='rgba(0, 0, 0, 0)',
                               paper_bgcolor='rgba(0, 0, 0, 0)',
                               showlegend=False)
        return line_fig

    if i_time_frame == "Start Minute":
        filtered_df = (filtered_df[["Start Minute", "Volume Discharged", "Source Type"]].groupby(
            by=["Start Minute", "Source Type"], as_index=False).sum())
        line_fig = px.line(data_frame=filtered_df.sort_values(by=i_time_frame, ascending=True),
                           x=i_time_frame,
                           y="Volume Discharged",
                           color="Source Type",
                           line_group="Source Type",
                           title=f"<b>Volume Discharged by {i_time_frame}<b>",
                           template="seaborn")
        line_fig.update_layout(margin=MARGIN_DICT,
                               plot_bgcolor='rgba(0, 0, 0, 0)',
                               paper_bgcolor='rgba(0, 0, 0, 0)',
                               showlegend=False)
        return line_fig

    # Bar Charts
    if i_time_frame == "Start Hour":
        filtered_df = (filtered_df[[i_time_frame, "Volume Discharged", "Source Type"]].groupby(
            by=[i_time_frame, "Source Type"], as_index=False).sum())
        bar_fig = px.histogram(data_frame=filtered_df,
                               x=i_time_frame,
                               y="Volume Discharged",
                               color="Source Type",
                               title=f"<b>Volume Discharged by {i_time_frame}<b>",
                               barmode="group",
                               template="seaborn")
        bar_fig.update_layout(margin=MARGIN_DICT,
                              plot_bgcolor='rgba(0, 0, 0, 0)',
                              paper_bgcolor='rgba(0, 0, 0, 0)',
                              showlegend=False)
        return bar_fig

    if i_time_frame == "Week day":
        filtered_df = (filtered_df[[i_time_frame, "Volume Discharged", "Source Type"]].groupby(
            by=[i_time_frame, "Source Type"], as_index=False).sum())
        bar_fig = px.histogram(data_frame=filtered_df,
                               x=i_time_frame,
                               y="Volume Discharged",
                               color="Source Type",
                               title=f"<b>Volume Discharged by {i_time_frame}<b>",
                               barmode="group",
                               template="seaborn")
        bar_fig.update_layout(margin=MARGIN_DICT,
                              plot_bgcolor='rgba(0, 0, 0, 0)',  # transparent plot area
                              paper_bgcolor='rgba(0, 0, 0, 0)',
                              showlegend=False)
        return bar_fig


# Asset performance viewer - barplot
@callback(
    Output("content-asset-performance-fig", "figure"),
    [Input("year-dropdown", "value"),
     Input("season-dropdown", "value"),
     Input("area-dropdown", "value"),
     Input("month-dropdown", "value"),
     Input("discharge-duration-radio", "value"),
     Input("best-worst-radio", "value"),
     Input("assets-shown-input", "value"),
     Input("sidebar-date-picker-range", "start_date"),
     Input("sidebar-date-picker-range", "end_date")])
def update_content_asset_bar(i_year, i_season, i_area, i_month, discharge_time, best_worst, num_shown, i_start_date,
                             i_end_date):
    filtered_df = filter_df(df, i_year, i_season, i_area, i_month, i_start_date, i_end_date)

    if filtered_df.empty:
        empty_fig = px.pie(names=["No Data"],
                           values=[1],
                           title="Please reselect your filters (e.g., Date range)",
                           template="seaborn")
        empty_fig.update_layout(margin=MARGIN_DICT,
                                plot_bgcolor='rgba(0, 0, 0, 0)',
                                paper_bgcolor='rgba(0, 0, 0, 0)')
        return empty_fig

    # Filter df and return number of assets
    filtered_df = filtered_df[["Asset Name", "Source Type", "Volume Discharged", "Duration Mins"]]
    max_assets = len(np.unique(filtered_df["Asset Name"]))

    # Create a total duration mins and total discharge mins column (for sorting on) for each asset
    filtered_df["asset_total_duration_mins"] = filtered_df.groupby(by=["Asset Name", "Source Type"])[
        "Duration Mins"].transform("sum")
    filtered_df["asset_total_volume_discharged"] = filtered_df.groupby(by=["Asset Name", "Source Type"])[
        "Volume Discharged"].transform("sum")

    if num_shown > max_assets or num_shown <= 0 or num_shown is None:
        num_shown = 1

    # Determine sorting order based on 'Best' or 'Worst' selection
    ascending_order = (best_worst == "Best")

    # Group, sum, and sort the DataFrame by the user metric choice
    if discharge_time == "Volume Discharged":
        grouped_df = (filtered_df.groupby(["Asset Name", "Source Type"], as_index=False)
                      .sum()
                      .sort_values(by="asset_total_volume_discharged",
                                   ascending=ascending_order)
                      .head(num_shown)).reset_index(drop=True)
        # Get the order of "Asset Name" based on sorted values
        category_order = grouped_df.sort_values(by="asset_total_volume_discharged", ascending=ascending_order)[
            "Asset Name"].tolist()

    elif discharge_time == "Duration Mins":
        grouped_df = (filtered_df.groupby(["Asset Name", "Source Type"], as_index=False)
                      .sum()
                      .sort_values(by="asset_total_duration_mins",
                                   ascending=ascending_order)
                      .head(num_shown)).reset_index(drop=True)
        # Get the order of "Asset Name" based on sorted values
        category_order = grouped_df.sort_values(by="asset_total_duration_mins", ascending=ascending_order)[
            "Asset Name"].tolist()

        # Generate bar plot
    bar_plot = px.bar(
        data_frame=grouped_df,
        x="Asset Name",
        y=discharge_time,
        color="Source Type",
        barmode="stack",
        title=f"<b>Asset Performance by {discharge_time}<b>",
        template="seaborn",
        hover_name="Asset Name",
        category_orders={"Asset Name": category_order})

    bar_plot.update_layout(
        margin=MARGIN_DICT,
        plot_bgcolor='rgba(0, 0, 0, 0)',
        paper_bgcolor='rgba(0, 0, 0, 0)',
        showlegend=False
    )

    return bar_plot


# Horizontal Box Plots of Volume Discharged and Duration
@callback(Output("content-box-fig", "figure"),
          [Input("year-dropdown", "value"),
           Input("season-dropdown", "value"),
           Input("area-dropdown", "value"),
           Input("month-dropdown", "value"),
           Input("box-measure-radio", "value"),
           Input("sidebar-date-picker-range", "start_date"),
           Input("sidebar-date-picker-range", "end_date")])
def update_overflow_distribution(i_year, i_season, i_area, i_month, i_box_measure, i_start_date, i_end_date):
    filtered_df = filter_df(df, i_year, i_season, i_area, i_month, i_start_date, i_end_date)

    if filtered_df.empty:
        empty_fig = px.pie(names=["No Data"],
                           values=[1],
                           title="Please reselect your filters (e.g., Date range)",
                           template="seaborn")
        empty_fig.update_layout(margin=MARGIN_DICT,
                                plot_bgcolor='rgba(0, 0, 0, 0)',
                                paper_bgcolor='rgba(0, 0, 0, 0)')
        return empty_fig

    # Make log_y if more than 4 orders of magnitude (oom) difference between min and max
    diff = np.max(filtered_df[i_box_measure]) - np.min(filtered_df[i_box_measure])
    oom = math.floor(math.log(diff, 10))

    if oom >= 5:

        boxplot = px.box(data_frame=filtered_df,
                         y="Source Type",
                         x=i_box_measure,
                         color="Source Type",
                         orientation="h",
                         template="seaborn",
                         hover_name="Asset Name",
                         hover_data=["Duration Mins"],
                         title=f"<b>{i_box_measure}<b>",
                         log_x=True)
        boxplot.update_layout(margin=MARGIN_DICT,
                              paper_bgcolor="rgba(0,0,0,0)",
                              plot_bgcolor="rgba(0,0,0,0)",
                              hovermode=False,
                              showlegend=False)
        boxplot.update_traces(hoverinfo="skip")
        return boxplot
    else:
        boxplot = px.box(data_frame=filtered_df,
                         y="Source Type",
                         x=i_box_measure,
                         color="Source Type",
                         orientation="h",
                         template="seaborn",
                         hover_name="Asset Name",
                         hover_data=["Duration Mins"],
                         title=f"<b>{i_box_measure}<b>",
                         log_x=False)

    boxplot.update_layout(margin=MARGIN_DICT,
                          paper_bgcolor="rgba(0,0,0,0)",
                          plot_bgcolor="rgba(0,0,0,0)",
                          hovermode=False,
                          showlegend=False)
    boxplot.update_traces(hoverinfo="skip")

    return boxplot


# Run application
if __name__ == "__main__":
    app.run(debug=True)  # run_serverfor deployed version
