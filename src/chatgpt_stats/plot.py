from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from loguru import logger
import click

from .extract import process_zip


def plot_data(all_messages):
    """
    Plots a stacked bar chart showing token counts by date and role, with enhanced formatting.
    Annotates each bar with the total cost.

    Args:
        all_messages (list): List of dictionaries containing message details.
    """
    # Create a DataFrame
    logger.info("Creating DataFrame for plotting")
    df = pd.DataFrame(all_messages)

    # Convert timestamps to dates
    df["date"] = pd.to_datetime(df["create_time"], unit="s").dt.date

    # Calculate total cost per message
    df["total_cost"] = df["cost"]

    # Group data by date and role for plotting
    num_tokens_by_date_and_user = (
        df.groupby(["date", "role"])[["num_tokens"]]
        .sum()
        .reset_index()
        .pivot(columns="role", index="date", values="num_tokens")
    )

    # Group data by date for total cost annotation
    total_cost_by_date = df.groupby("date")["total_cost"].sum()

    # Generate a stacked bar chart
    logger.info("Generating stacked bar chart with enhanced formatting")
    ax = num_tokens_by_date_and_user.plot(
        kind="bar",
        stacked=True,
        figsize=(12, 6),
        alpha=0.85,
        title="Token Count by Date and Role",
    )

    # Annotate bars with total cost
    for i, (date, total_cost) in enumerate(total_cost_by_date.items()):
        ax.annotate(
            f"${total_cost:.2f}",
            xy=(i, num_tokens_by_date_and_user.loc[date].sum()),
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
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"{int(x / 1000)}k"))

    # Set axis labels and legend
    ax.set_xlabel("Date")
    ax.set_ylabel("Number of Tokens")
    ax.legend(title="Role")
    plt.tight_layout()
    plt.show()
    logger.info("Plot displayed successfully")


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
def main(zip_path: Path, extract_to: Path):
    """
    Process a ZIP file and plot token counts.

    ZIP_PATH: Path to the ZIP file to process.
    """
    # Configure logging
    logger.info(f"Starting script with ZIP_PATH={zip_path} and EXTRACT_TO={extract_to}")

    try:
        # Process the ZIP file and get messages
        all_messages = process_zip(zip_path, extract_to)

        # Plot the data
        plot_data(all_messages)

    except Exception as e:
        logger.error(f"An error occurred: {e}")
        raise


if __name__ == "__main__":
    main()
