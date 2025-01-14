from pathlib import Path
import datetime
from typing import Optional

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from loguru import logger
import click

from .extract import process_zip


# TODO: make to_count an enum
def plot_data(all_messages, to_count: str, since: datetime.date = None):
    """
    Plots a stacked bar chart showing token counts by date and role, with enhanced formatting.
    Annotates each bar with the total cost and includes the total cost in the title.

    Args:
        all_messages (list): List of dictionaries containing message details.
    """

    # Create a DataFrame
    logger.info("Creating DataFrame for plotting")
    df = pd.DataFrame(all_messages)

    # Convert timestamps to dates
    df["date"] = pd.to_datetime(df["create_time"], unit="s").dt.date

    # If "since" specified, filter
    if since:
        df = df.loc[df["date"] >= since]

    # Calculate total cost per message
    df["total_cost"] = df["cost"]

    # Group data by date and role for plotting

    if to_count == "token":
        col_name = "num_tokens"
        count = df.groupby(["date", "role"])[[col_name]].sum()
    elif to_count == "message":
        col_name = "msg_id"
        count = df.groupby(["date", "role"])[[col_name]].count()

    else:
        raise ValueError(f"Cannot count {to_count}s")
    num_by_date_and_user = count.reset_index().pivot(
        columns="role", index="date", values=col_name
    )

    # Group data by date for total cost annotation
    total_cost_by_date = df.groupby("date")["total_cost"].sum()

    # Calculate the total cost across all days
    total_cost_all_days = total_cost_by_date.sum()

    # Generate a stacked bar chart
    logger.info("Generating stacked bar chart with enhanced formatting")
    ax = num_by_date_and_user.plot(
        kind="bar",
        stacked=True,
        figsize=(12, 6),
        alpha=0.85,
        title=f"{to_count.capitalize()} Count by Date and Role (Total Cost: ${total_cost_all_days:.2f})",
    )

    # Annotate bars with total cost
    for i, (date, total_cost) in enumerate(total_cost_by_date.items()):
        ax.annotate(
            f"${total_cost:.2f}",
            xy=(i, num_by_date_and_user.loc[date].sum()),
            xytext=(0, 5),  # Offset above the bar
            textcoords="offset points",
            ha="center",
            fontsize=10,
            color="black",
            weight="bold",
        )

    # Add gridlines
    ax.yaxis.grid(True, which="major", linestyle="--", linewidth=0.7, alpha=0.7)
    ax.set_axisbelow(True)  # Ensure gridlines are behind the bars

    # Format y-axis labels in multiples of 1000
    if to_count == "token":
        ax.yaxis.set_major_formatter(
            ticker.FuncFormatter(lambda x, _: f"{int(x / 1000)}k")
        )

    # Set axis labels and legend
    ax.set_xlabel("Date")
    ax.set_ylabel(f"Number of {to_count.capitalize()}s")
    ax.legend(title="Role")
    plt.tight_layout()
    plt.show()
    logger.info("Plot displayed successfully")


def parse_timedelta(arg):
    """
    Parse a string like "days=7" or "weeks=4" into a timedelta object.

    Args:
        arg (str): String representing the timedelta (e.g., "days=7", "weeks=4").

    Returns:
        timedelta: A timedelta object representing the parsed duration.

    Raises:
        ValueError: If the input string is not in the correct format.
    """
    try:
        # Split the string into key and value
        key, value = arg.split("=")
        value = int(value)  # Convert the value to an integer
        # Create and return the corresponding timedelta
        return datetime.timedelta(**{key: value})
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid format for timedelta argument: {arg}") from e


@click.command()
@click.argument(
    "zip_path", type=click.Path(exists=True, dir_okay=False, path_type=Path)
)
@click.option(
    "--extract-to",
    type=click.Path(dir_okay=False, writable=True, path_type=Path),
    default="/tmp/conversations.json",
    help="Path to extract conversations.json",
    show_default=True,
)
@click.option(
    "--since",
    default=None,
    help="Show data since timedelta (days|weeks=*)",
)
@click.option(
    "--to-count",
    type=str,
    default="token",
    show_default=True,
)
def main(zip_path: Path, extract_to: Path, since: Optional[str], to_count: str):
    """
    Process a ZIP file and plot token counts.

    ZIP_PATH: Path to the ZIP file to process.
    """
    # Configure logging
    logger.info(f"Starting script with ZIP_PATH={zip_path} and EXTRACT_TO={extract_to}")

    if since:
        try:
            units, values = since.split("=")
            since = datetime.date.today() - datetime.timedelta(**{units: float(values)})
            click.echo(f"Displaying stats from {since}")
        except ValueError as e:
            click.echo(f"Error: {e}")
    else:
        click.echo("No cutoff date provided. Displaying all stats.")

    try:
        # Process the ZIP file and get messages
        all_messages = process_zip(zip_path, extract_to)

        # Plot the data
        plot_data(all_messages, to_count=to_count, since=since)

    except Exception as e:
        logger.error(f"An error occurred: {e}")
        raise


if __name__ == "__main__":
    main()
