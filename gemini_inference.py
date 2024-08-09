import argparse
import os
import vertexai
from vertexai.generative_models import GenerativeModel, Part, FinishReason
import vertexai.preview.generative_models as generative_models
from bs4 import BeautifulSoup

# Modules
from shared import log_message as logr

def count_chars_and_tokens(model_id, content):
    model = GenerativeModel(model_id)
    num_chars = len(content)
    num_tokens = model.count_tokens(content).total_tokens
    return { "num_chars" : num_chars, "num_tokens" : num_tokens } 

def run_text_inference(payload, prompt, type, model_id, verbose=False):
    # Initialize Vertex AI
    vertexai.init(project=os.getenv("VERTEX_IA_PROJECT"), location=os.getenv("VERTEX_IA_REGION"))

    # Extract the body content using BeautifulSoup if payload is from a file
    if type == "file":
        with open(payload, "r") as html_file:
            payload = html_file.read()
        soup = BeautifulSoup(payload, 'html.parser')
        body_text = soup.body.get_text()
    else:
        body_text = payload

    # Define generation and safety settings
    generation_config = {
        "max_output_tokens": 8192,
        "temperature": 1,
        "top_p": 0.95,
    }

    safety_settings = {
        generative_models.HarmCategory.HARM_CATEGORY_HATE_SPEECH: generative_models.HarmBlockThreshold.BLOCK_NONE,
        generative_models.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: generative_models.HarmBlockThreshold.BLOCK_NONE,
        generative_models.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: generative_models.HarmBlockThreshold.BLOCK_NONE,
        generative_models.HarmCategory.HARM_CATEGORY_HARASSMENT: generative_models.HarmBlockThreshold.BLOCK_NONE,
    }

    # Load the generative model
    model = GenerativeModel(model_id)
    if verbose:
        print(f'PROMPT: {prompt}')
        print(f'PROMPT SIZE: {len(prompt)}')
    # Generate content
    response = model.generate_content(
        [body_text, prompt],
        generation_config=generation_config,
        safety_settings=safety_settings,
        stream=False,
    )
    if verbose:
        logr(response.candidates[0].content.parts[0].text)
    return response.candidates[0].content.parts[0].text


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Summarize an HTML file or input string using Vertex AI's generative model.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-u", "--html_uri", type=str, help="The URI path to the HTML file.")
    group.add_argument("-i", "--input", type=str, help="The input string to be summarized.")
    parser.add_argument("-t", "--type", type=str, default="file", choices=["file", "string"], help="Type of input: file or string")
    parser.add_argument("-p", "--prompt", type=str, default="Summarize this article in 5 sentences.", help="The prompt to be passed to the generative model.")
    parser.add_argument("-m", "--model", type=str, default="gemini-1.5-flash-001", choices=["gemini-1.5-flash-001", "gemini-1.5-pro-001"], help="The Gemini model to use")
    parser.add_argument("-v", "--verbose", action='store_true', help="Print output to console")
    args = parser.parse_args()

    if args.html_uri and args.type == "file":
        run_text_inference(args.html_uri, args.prompt, args.type, args.model,args.verbose)
    elif args.input and args.type == "string":
        run_text_inference(args.input, args.prompt, args.type, args.model,args.verbose)
    else:
        parser.log_message_help()