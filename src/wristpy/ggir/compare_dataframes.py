"""Comparing GGIR outputs to wristpy outputs for epoch 1."""

import pathlib
from datetime import timedelta

import numpy as np
import plotly.graph_objects as go
import polars as pl
import statsmodels.api as sm
from matplotlib import pyplot as plt
from statsmodels.graphics.gofplots import qqplot_2samples

from wristpy.common.data_model import OutputData


def load_ggir_output(filepath: pathlib.Path) -> pl.DataFrame:
    """Load ggir output.csv.

    Args:
        filepath: is the Path to the GGIR output .csv to load

    Returns:
        A polars data frame with the GGIR enmo, anglez, and timestamps. Timestamps have
        been sliced to remove timezone information
    """
    ggir_data = pl.read_csv(filepath, dtypes={"ENMO": pl.Float64})
    ggir_data = ggir_data.with_columns(pl.col("timestamp").str.slice(0, 19))

    return ggir_data



def select_days(
    df: pl.DataFrame, start_day: int = 0, end_day: int | None = None
) -> pl.DataFrame:  
    """Selects a subset of the dataframes, from days start:end, based on user input.

    Args:
        df: the given dataframe from which we will take data from the given data range.

        start_day: The int specifying on which day the user would like to begin taking
        data from. If no date is given, data begins from the first day. Day 1 begins at
        an arbitrary hour, any other start_day will begin at midnight.

        end_day: the int specifying on which day the user would like to stop taking data
        If no date is given, data is extracted through the end. The last day present in
        the dataframe ends at an arbbitrary hour, any other end_day will end just
        before midnight.

    Returns:
        filtered_df = the subset of the input dataframe, based on the date range given.
    """
    min_timestamp = df["time"].min()
    max_timestamp = df["time"].max()
    # Calculate the total days spanned by the data.
    total_days = (max_timestamp - min_timestamp).days + 1

    # Determine the start timestamp.
    if start_day > 1:
        start_timestamp = (
            min_timestamp + timedelta(days=start_day - 1)
            ).replace(
                hour=0, 
                minute=0,
                second=0, 
                microsecond=0
        )
    else:
        start_timestamp = min_timestamp

    # Determine the end timestamp.
    if end_day and end_day < total_days:
        end_timestamp = (
            min_timestamp + timedelta(days=end_day)
            ).replace(
                hour=0, 
                minute=0, 
                second=0, 
                microsecond=0) - timedelta(microseconds=1)
    else:
        end_timestamp = max_timestamp


    # Filter the dataframe based on calculated timestamps.
    filtered_df = df.filter(
        (pl.col("time") >= start_timestamp) & (pl.col("time") <= end_timestamp)
    )
    
    return filtered_df


def compare(
    ggir_dataframe: pl.DataFrame, wristpy_dataframe: OutputData
) -> pl.DataFrame:
    """Compares a wristpy and ggir dataframe.

    Args:
        ggir_dataframe:
            The GGIR derived dataframe to be used to calculate difference between GGIR
            and wristpy outputs.

        wristpy_dataframe:
            The wristpy OutputData object to be used to calculate difference between
            GGIR and wristpy outputs.

    Returns:
        epoch1_data_time_match: A dataframe with epoch1 timestamps that are matched
        between wristpy and GGIR, contains enmo, anglez for both processing tools, as
        well as the non-wear flag from wristpy.
    """
    ggir_time = pl.Series(ggir_dataframe["timestamp"])

    ggir_datetime = ggir_time.str.to_datetime(time_unit="ns")

    epoch1_wristpy = pl.DataFrame(
        {
            "time_epoch1": wristpy_dataframe.time_epoch1,
            "enmo_wristpy": wristpy_dataframe.enmo_epoch1,
            "anglez_wristpy": wristpy_dataframe.anglez_epoch1,
            "non_wear_flag": wristpy_dataframe.non_wear_flag_epoch1,
        }
    )

    epoch1_ggir = pl.DataFrame(
        {
            "time_epoch1": ggir_datetime,
            "enmo_ggir": ggir_dataframe["ENMO"],
            "anglez_ggir": ggir_dataframe["anglez"],
        }
    )

    epoch1_data_time_match = epoch1_wristpy.join(
        epoch1_ggir, left_on="time_epoch1", right_on="time_epoch1", how="inner"
    )

    return epoch1_data_time_match


def compare_csv(
    ggir_dataframe: pl.DataFrame, wristpy_dataframe: pl.DataFrame
) -> pl.DataFrame:
    """Compares a wristpy and ggir dataframe, loaded from csv.

    Args:
        ggir_dataframe:
            The GGIR derived dataframe to be used to calculate difference between GGIR
            and wristpy outputs.
        wristpy_dataframe:
            The wristpy dataframe to be used to calculate difference between GGIR and
              wristpy output, loaded from csv.


    Returns:
        epoch1_data_time_match: A dataframe with epoch1 timestamps that are matched
        between wristpy and GGIR, contains enmo, anglez for both processing tools, as
        well as the non-wear flag from wristpy.
    """
    ggir_time = pl.Series(ggir_dataframe["timestamp"])

    ggir_datetime = ggir_time.str.to_datetime(time_unit="ns")

    wristpy_time = pl.Series(wristpy_dataframe["time"])
    wrispty_datetime = wristpy_time.str.to_datetime(time_unit="ns")

    epoch1_wristpy = pl.DataFrame(
        {
            "time_epoch1": wrispty_datetime,
            "enmo_wristpy": wristpy_dataframe["enmo"],
            "anglez_wristpy": wristpy_dataframe["anglez"],
            "non_wear_flag": wristpy_dataframe["Non-wear Flag"],
        }
    )

    epoch1_ggir = pl.DataFrame(
        {
            "time_epoch1": ggir_datetime,
            "enmo_ggir": ggir_dataframe["ENMO"],
            "anglez_ggir": ggir_dataframe["anglez"],
        }
    )

    epoch1_data_time_match = epoch1_wristpy.join(
        epoch1_ggir, left_on="time_epoch1", right_on="time_epoch1", how="inner"
    )

    return epoch1_data_time_match


def plot_qq(
    output_data_trimmed: pl.DataFrame, ggir_data1: pl.DataFrame, measure: str
) -> None:
    """Create a Quantile-Quantile plot comparing the two samples from wristpy and ggir.

    Args:
        output_data_trimmed: A dataframe with wristpy output data. Plotted on x-axis
        ggir_data1: A dataframe with ggir output data. Plotted on y-axis
        measure: The name of the measure to be compared within each dataframe

    Returns:
        None
    """
    pp_x = sm.ProbPlot(output_data_trimmed[measure])
    pp_y = sm.ProbPlot(ggir_data1[measure])
    qqplot_2samples(pp_x, pp_y, line="r")
    plt.title(f"QQ plot - {measure}")
    plt.xlabel("wristpy")
    plt.ylabel("ggir")
    plt.show()


def plot_ba(
    output_data_trimmed: pl.DataFrame, ggir_data1: pl.DataFrame, measure: str
) -> None:
    """Bland Altman plot comparing differences and means of two samples.

    Args:
        output_data_trimmed: A dataframe with wristpy output data. 
        ggir_data1: A dataframe with ggir output data.

        measure: The name of the measure to be compared within each dataframe

    Returns:
        None.
    """
    opac_dict = dict(alpha=0.5)
    f, ax = plt.subplots(1, figsize = (8,5))
    sm.graphics.mean_diff_plot(np.asarray(output_data_trimmed[measure]), np.asarray(ggir_data1[measure]), ax = ax, scatter_kwds=opac_dict)
    plt.title(f'BA plot - {measure}')
    plt.show()    


def plot_measure(
    difference_df: pl.DataFrame,
    outputdata_trimmed: pl.DataFrame,
    ggir_dataframe: pl.DataFrame,
    opacity: float,
    measure: str,
) -> None:
    """Plot the time series for a given measure.

    Args:
        difference_df: Dataframe with time and error difference
        outputdata_trimmed: Dataframe with the outputData class trimmed for comparison
        ggir_dataframe: Dataframe with ggir data
        opacity: For data overlay visibility
        measure: measure being plotted.

        Returns:None
    """
    fig = go.Figure()

    # Add the trimmed anglez from outputdata_trimmed
    fig.add_trace(go.Scatter(x=difference_df["timestamp"],
                            y=outputdata_trimmed[measure],
                            mode='lines',
                            line=dict(color='green', width=2),
                            name=f'Wristpy {measure} (Trimmed)',
                            opacity=opacity))

    # Add the anglez from ggir_dataframe
    fig.add_trace(go.Scatter(x=difference_df["timestamp"],
                            y=ggir_dataframe[measure],
                            mode='lines+markers', # Change to 'lines' if you don't want markers
                            line=dict(color='red', dash='dash', width=2),
                            name=f'GGIR {measure}',
                            opacity=opacity
                            ))

    # Add the anglez difference
    fig.add_trace(go.Scatter(x=difference_df["timestamp"],
                            y=difference_df[measure],
                            mode='lines',
                            line=dict(color='black', width=2),
                            name=f'{measure} Difference'))

    # Update the layout with titles and labels
    fig.update_layout(
        title=f"{measure} Comparison",
        xaxis_title="Time",
        yaxis_title=f"{measure} Values",
        legend_title="Legend",
    )

    # Show the figure
    fig.show()


def plot_diff(
    difference_df: pl.DataFrame,
    outputdata_trimmed: pl.DataFrame,
    ggir_dataframe: pl.DataFrame,
    opacity: float,
    measure: str,
    plot: str,
) -> None:
    """Plot difference graphs, with user defined indices, opacity and measures.

    Args:
        difference_df: Dataframe with time and error difference

        outputdata_trimmed: Dataframe with the outputData class trimmed for comparison

        ggir_dataframe: Dataframe with ggir data

        opacity: For data overlay visibility

        measure: user defined measure to plot and compare.

        plot: The type of plot type specified by the user. ts will plot the timeseries
        data of wristpy output, ggir output and the differences between the two. ba
        will create a Bland Altman plot, qq will create a Quantile-Quantile plot.

    Returns:
            None
    """
    if plot == "ts":
        plot_measure(
            difference_df=difference_df,
            outputdata_trimmed=outputdata_trimmed,
            ggir_dataframe=ggir_dataframe,
            measure=measure,
            opacity=opacity,
        )
    elif plot == "ba":
        plot_ba(
            output_data_trimmed=outputdata_trimmed,
            ggir_data1=ggir_dataframe,
            measure=measure,
        )
    elif plot == "qq":
        plot_qq(
            output_data_trimmed=outputdata_trimmed,
            ggir_data1=ggir_dataframe,
            measure=measure,
        )
    else:
        print("YOU DID NOT SELECT A PLOT!")
