from pathlib import Path
import zipfile
import shutil
import json
from typing import Any

from loguru import logger

from .pricing import COST_PER_TOKEN


def extract_file_from_zip(zip_path: Path, file_to_extract: str, destination: Path):
    """
    Extracts a single file from a ZIP archive.

    Args:
        zip_path (Path): Path to the ZIP file.
        file_to_extract (str): Name of the file inside the ZIP archive to extract.
        destination (Path): Path to the desired destination (can be a directory or a file path).

    Returns:
        Path: The Path to the extracted file if successful.

    Raises:
        FileNotFoundError: If the ZIP file or the file to extract is not found.
    """
    # Ensure the provided paths are Path objects
    zip_path = Path(zip_path)
    destination = Path(destination)

    if not zip_path.exists():
        logger.error(f"The ZIP file '{zip_path}' does not exist.")
        raise FileNotFoundError(f"The ZIP file '{zip_path}' does not exist.")

    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        # Check if the file exists in the ZIP archive
        if file_to_extract not in zip_ref.namelist():
            logger.error(
                f"The file '{file_to_extract}' was not found in the ZIP archive."
            )
            raise FileNotFoundError(
                f"The file '{file_to_extract}' was not found in the ZIP archive."
            )

        # Determine if destination is a file or directory
        if destination.is_dir():
            # Extract to the directory
            extracted_path = zip_ref.extract(file_to_extract, path=destination)
            logger.info(f"Extracted '{file_to_extract}' to directory '{destination}'")
        else:
            # Extract to a temporary directory, then move to the desired file path
            temp_file_path = zip_ref.extract(file_to_extract)
            extracted_path = destination
            shutil.move(temp_file_path, destination)
            logger.info(f"Extracted '{file_to_extract}' to file '{destination}'")

        return Path(extracted_path)


def extract_message_details(
    conversation: dict[str, Any],
    chars_per_token: int,
    cost_per_token: dict[str, dict[str, float]] = COST_PER_TOKEN,
):
    """
    Extracts message details from a conversation, calculates the cost, and returns processed messages.

    Args:
        conversation (dict): The conversation data.
        chars_per_token (int): Approximation of characters per token.
        cost_per_token (dict): Pricing dictionary for token costs.

    Returns:
        list: A list of dictionaries containing message details and costs.
    """
    processed_messages = []
    mapping = conversation.get("mapping", {})

    # initialise model as 4o, since the conversations don't log the model until the first
    # assistant response
    model = "gpt-4o"
    for node in mapping.values():
        # Extract the message object and validate its structure
        message = node.get("message")
        if not message:
            continue

        content = message.get("content", {}).get("parts", [])
        if not content:
            continue

        role = message.get("author", {}).get("role")
        if not role:
            continue

        # Determine the model slug and pricing details
        metadata = message.get("metadata", {})
        model = metadata.get("model_slug", model)  # default to last used
        pricing = cost_per_token.get(model, {"input": 0, "output": 0})

        # Calculate token count and cost
        content_length = len(content[0])
        num_tokens = content_length / chars_per_token
        cost = (
            pricing["input"] * num_tokens
            if role == "user"
            else pricing["output"] * num_tokens
        )

        # Append processed message details
        processed_messages.append(
            {
                "conv_id": conversation.get("id", "unknown_id"),
                "msg_id": message.get("id", "unknown_msg_id"),
                "create_time": message.get("create_time", 0),
                "role": f"{role}:{model}" if role == "assistant" else role,
                "content": content[0],
                "num_tokens": num_tokens,
                "model": model,
                "cost": cost,
            }
        )

    return processed_messages


def process_conversations(data, chars_per_token=4):
    """
    Processes a list of conversations and extracts message details.

    Args:
        data (list): List of conversation dictionaries.
        chars_per_token (int): Approximation of characters per token.

    Returns:
        list: A list of dictionaries containing message details from all conversations.
    """
    all_messages = []
    logger.info("Processing conversations...")

    for conversation in data:
        conversation_id = conversation.get("id", "unknown_id")
        logger.debug(f"Processing conversation ID: {conversation_id}")

        # Extract message details for the current conversation
        messages = extract_message_details(conversation, chars_per_token)
        all_messages.extend(messages)

    logger.info(
        f"Processed {len(all_messages)} messages from {len(data)} conversations"
    )
    return all_messages


@logger.catch
def process_zip(zip_path, extract_to):
    # Extract conversations.json from the ZIP file
    logger.info(f"Extracting conversations.json from {zip_path} to {extract_to}")
    try:
        extracted_path = extract_file_from_zip(
            Path(zip_path), "conversations.json", Path(extract_to)
        )
    except Exception as e:
        logger.error(f"Failed to extract conversations.json: {e}")
        raise

    logger.info(f"Successfully extracted conversations.json to {extracted_path}")

    # Load the JSON data
    try:
        data = json.load(extracted_path.open("r"))
    except Exception as e:
        logger.error(f"Failed to load JSON data: {e}")
        raise

    logger.info("Successfully loaded JSON data")

    # Prepare list to store token counts
    all_messages = []
    chars_per_token = 4  # Approximation factor (4 characters ≈ 1 token)

    logger.info("Processing conversations...")
    all_messages = process_conversations(data, chars_per_token=chars_per_token)
    logger.info(f"Processed {len(all_messages)} messages")

    return all_messages
