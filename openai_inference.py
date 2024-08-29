import argparse
import os
import tiktoken
import tempfile
from openai import OpenAI
from bs4 import BeautifulSoup

from pydub import AudioSegment

# Modules
from shared import log_message as logr

def count_chars_and_tokens(model_id, content):
    encoding = tiktoken.encoding_for_model(model_id)
    num_tokens = len(encoding.encode(content))
    num_chars = len(content)
    return { "num_chars" : num_chars, "num_tokens" : num_tokens } 

def run_text_inference(payload, prompt, type, model_id, verbose=False):
    # Initialize OpenAI client
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    # Extract the body content using BeautifulSoup if payload is from a file
    if type == "file":
        with open(payload, "r") as html_file:
            payload = html_file.read()
        soup = BeautifulSoup(payload, 'html.parser')
        body_text = soup.body.get_text()
    else:
        body_text = payload

    # Prepare the message for OpenAI Chat Completion
    message = f"Content: {body_text}\n\n{prompt}"

    # Generate content using the Chat Completions API
    response = client.chat.completions.create(
        model=model_id,
        messages=[
            {"role": "user", "content": message}
        ],
        max_tokens=16384,
        temperature=1,
    )
    # Log and return the response
    if verbose:
        print(response.choices[0].message.content)
    return response.choices[0].message.content

def transcribe_audio(file_path, model="whisper-1", sampled=False):
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    temp_file_path = None
    try:
        if sampled:
            # Load the audio file
            audio = AudioSegment.from_file(file_path)

            # Extract the first 5 minutes (or less if the file is shorter)
            duration_ms = 60000  # 300000 ms = 5 minutes
            first_5_minutes = audio[:duration_ms]

            # Create a temporary file to store the extracted audio
            temp_file = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
            temp_file_path = temp_file.name
            first_5_minutes.export(temp_file_path, format="mp3")

            # Use the temporary file for transcription
            transcription_file = temp_file_path
        else:
            # Use the original file for transcription
            transcription_file = file_path

        # Transcribe the file
        with open(transcription_file, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                model=model,
                file=audio_file,
                timestamp_granularities=["segment"],
                response_format="verbose_json"
            )

        return transcription.text
    except Exception as e:
        print(f"An error occurred during transcription: {e}")
        return None
    finally:
        # Clean up the temporary file if it was created
        if temp_file_path and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
            # if 
            # print(f"Temporary file {temp_file_path} has been removed.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process content using OpenAI's models.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-u", "--html_uri", type=str, help="The URI path to the HTML file.")
    group.add_argument("-i", "--input", type=str, help="The input string to be processed.")
    parser.add_argument("-t", "--type", type=str, default="file", choices=["file", "string"], help="Type of input: file or string")
    parser.add_argument("-p", "--prompt", type=str, default="Summarize this article in 5 sentences.", help="The prompt to be passed to the model.")
    parser.add_argument("-m", "--model", type=str, default="gpt-3.5-turbo", choices=["gpt-3.5-turbo", "gpt-4"], help="The OpenAI model to use")
    parser.add_argument("-v", "--verbose", action='store_true', help="Print output to console")
    args = parser.parse_args()

    if args.html_uri and args.type == "file":
        run_text_inference(args.html_uri, args.prompt, args.type, args.model, args.verbose)
    elif args.input and args.type == "string":
        run_text_inference(args.input, args.prompt, args.type, args.model, args.verbose)
    else:
        parser.log_message_help()