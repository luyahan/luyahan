#!/usr/bin/env python3
"""Summarize log files using Anthropic API."""

import anthropic
import argparse
import sys
import os


def main():
    parser = argparse.ArgumentParser(
        description="Summarize log files using Anthropic API"
    )
    parser.add_argument(
        "file",
        nargs="?",
        type=str,
        help="Path to the log file to summarize (use - for stdin)"
    )
    parser.add_argument(
        "--system",
        default=None,
        help="System prompt for the API (default: from SUMMARY_PROMPT env var)"
    )

    args = parser.parse_args()

    # Get system prompt: env var > CLI arg > default
    system_prompt = os.environ.get("SUMMARY_PROMPT")

    # Read input
    if args.file is None or args.file == "-":
        content = sys.stdin.read()
    else:
        try:
            with open(args.file, "r") as f:
                content = f.read()
        except FileNotFoundError:
            print(f"Error: File '{args.file}' not found", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Error reading file: {e}", file=sys.stderr)
            sys.exit(1)

    if not content.strip():
        print("No content to summarize", file=sys.stderr)
        sys.exit(1)

    # Call API
    client = anthropic.Anthropic()

    message = client.messages.create(
        model="MiniMax-M2.1",
        max_tokens=4000,
        system=system_prompt,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"{system_prompt}:\n\n{content}"
                    }
                ]
            }
        ]
    )

    # Output result
    for block in message.content:
        if block.type == "thinking":
            continue
        elif block.type == "text":
            print(block.text)


if __name__ == "__main__":
    main()
