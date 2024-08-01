import argparse
import os
from anthropic import Anthropic
from bs4 import BeautifulSoup

# Modules
from shared import log_message as logr

def count_chars_and_tokens(model_id, prompt):
    anthropic = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    num_chars = len(prompt)
    num_tokens = anthropic.count_tokens(prompt)
    return num_chars, num_tokens

def run_text_inference(payload, prompt, type, model_id, verbose=False):
    # Initialize Anthropic client
    anthropic = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    # Extract the body content using BeautifulSoup if payload is from a file
    if type == "file":
        with open(payload, "r") as html_file:
            payload = html_file.read()
        soup = BeautifulSoup(payload, 'html.parser')
        body_text = soup.body.get_text()
    else:
        body_text = payload

    # Prepare the message for Claude
    message = f"Content: {body_text}\n\n{prompt}"

    # Generate content using the Messages API
    response = anthropic.messages.create(
        model=model_id,
        max_tokens=4096,
        temperature=1,
        messages=[
            {"role": "user", "content": message}
        ]
    )
    # Log and return the response
    if verbose:
        logr(response.content[0].text)
    return response.content[0].text


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process content using Anthropic's Claude model.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-u", "--html_uri", type=str, help="The URI path to the HTML file.")
    group.add_argument("-i", "--input", type=str, help="The input string to be processed.")
    parser.add_argument("-t", "--type", type=str, default="file", choices=["file", "string"], help="Type of input: file or string")
    parser.add_argument("-p", "--prompt", type=str, default="Summarize this article in 5 sentences.", help="The prompt to be passed to the Claude model.")
    parser.add_argument("-m", "--model", type=str, default="claude-3-5-sonnet-20240620", choices=["claude-3-5-sonnet-20240620","claude-3-opus-20240229"], help="The Claude model to use")
    parser.add_argument("-v", "--verbose", action='store_true', help="Print output to console")
    args = parser.parse_args()

    if args.html_uri and args.type == "file":
        run_text_inference(args.html_uri, args.prompt, args.type, args.model,args.verbose)
    elif args.input and args.type == "string":
        run_text_inference(args.input, args.prompt, args.type, args.model,args.verbose)
    else:
        parser.log_message_help()