import json
import time
from datetime import datetime, timedelta, timezone

import requests

import os
from dotenv import dotenv_values

from bs4 import BeautifulSoup
import truthbrush as tb
import ollama

CONFIG = dotenv_values(".env")

# Configuration
CHECK_INTERVAL = 300  # Check every 5 minutes (in seconds)

# File to store the latest post ID we've seen
LAST_POST_FILE = "last_trump_post.json"


def extract_paragraph_text(html_string):
    """
    Extracts all text from paragraph tags in an HTML string.

    Args:
        html_string (str): The HTML content as a string

    Returns:
        list: A list of strings, each containing the text from a paragraph
    """
    # Create a BeautifulSoup object to parse the HTML
    soup = BeautifulSoup(html_string, "html.parser")

    # Find all paragraph tags
    paragraphs = soup.find_all("p")

    # Extract the text from each paragraph
    paragraph_texts = [p.get_text().strip() for p in paragraphs]

    # Filter out empty paragraphs
    paragraph_texts = [text for text in paragraph_texts if text]

    return paragraph_texts


def get_latest_posts(since_id=None):
    try:
        api = tb.Api()
        created_after = None
        if since_id is None:
            created_after = datetime.now(timezone.utc) - timedelta(days=1)

        truths = api.pull_statuses(
            "realDonaldTrump", since_id=since_id, created_after=created_after
        )

        return list(truths)
    except Exception as e:
        print(f"Error fetching posts: {e}")
        return []


def analyze_with_llm(post_content):
    """
    Send the post content to an LLM to analyze potential stock market impact.
    """
    try:
        message = [
            {
                "role": "system",
                "content": """Based on the input tweet, is there a reasonable likelihood it could indicate a buy, sell or hold of stocks in the market?
                         Consider mentions of companies, industries, economic policies, trade deals, or other market-relevant information.
                         Answer with 'Yes' or 'No' first, followed by an explanation of 50 words or less.""",
            },
            {"role": "user", "content": post_content},
        ]

        output = ollama.chat(
            model=CONFIG["OLLAMA_MODEL"],
            messages=message,
        )

    except Exception as e:
        print(f"Error analyzing with LLM: {e}")
        return False, f"Error: {e}"
    else:
        response = output["message"]["content"]

        # Check if the analysis starts with "Yes"
        could_impact_market = response.startswith("Yes")

        return could_impact_market, response


def send_notification(content, analysis):
    """
    Send a push notification to iPhone with the post and analysis.
    """
    try:
        message = f"{content}\n\nAnalysis: {analysis}"
        requests.post(f"https://ntfy.sh/{CONFIG['NTFY_TOPIC']}", data=message)
        print(f"Notification sent at {datetime.now()}")
    except Exception as e:
        print(f"Error sending notification: {e}")


def save_last_post_id(post_id):
    """Save the ID of the last processed post."""
    with open(LAST_POST_FILE, "w") as f:
        json.dump({"last_post_id": post_id}, f)


def get_last_post_id():
    """Get the ID of the last processed post."""
    if os.path.exists(LAST_POST_FILE):
        with open(LAST_POST_FILE, "r") as f:
            data = json.load(f)
            return data.get("last_post_id")
    return None


def main():
    print(f"Starting Truth Social monitor at {datetime.now()}")

    ollama.pull(model=CONFIG["OLLAMA_MODEL"])

    last_post_id = get_last_post_id()
    print(f"Last processed post ID: {last_post_id}")

    while True:
        print(f"Checking for new posts at {datetime.now()}")
        posts = get_latest_posts(last_post_id)

        if not posts:
            print("No posts found or error occurred")
            time.sleep(CHECK_INTERVAL)
            continue

        # Sort posts by creation date (newest first)
        posts.sort(key=lambda x: x["created_at"], reverse=True)
        newest_post = posts[0]

        # If we've seen this post before, skip
        if newest_post["id"] == last_post_id:
            print("No new posts found")
            time.sleep(CHECK_INTERVAL)
            continue

        print(f"New post found: {newest_post['id']}")

        if content := "\n".join(extract_paragraph_text(newest_post["content"])):
            # Analyze the post
            could_impact_market, analysis = analyze_with_llm(content)

            if could_impact_market:
                print("Post could impact market. Sending notification.")
                send_notification(content, analysis)
            else:
                print("Post unlikely to impact market.")

        # Update the last post ID
        save_last_post_id(newest_post["id"])
        last_post_id = newest_post["id"]

        # Wait before checking again
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
