#!/usr/bin/python3
import argparse
import sys
import time
import gemini_inference
import claude_inference
from usescraper_wrapper import create_scrape_job, get_job_info, get_scraped_data
from shared import scraper_api, convert_integer_to_decimal, convert_string_to_list
from shared import log_message as logr

# DEPENDENCIES_FOLDER ='../../llm-agents' 
# sys.path.append(DEPENDENCIES_FOLDER)

def main(url, prompt, scrapeuse_token, download_folder, model_id):
    # stage #1 Scraper
    logr(f"starting stage #1 scraper")
    crawler = scraper_api(url, "raw-html", 3000)
    if not crawler.content:
        logr(f"Crawling failed to return content!")
        return False

    # if "html_body" not in crawler.content:
    #     logr("error: HTML body not found in the result.")
    #     return

    topic = crawler.url.split('/')[3]
    payload = str(crawler.content)
    if prompt is None:
        prompt = f"""
        You are a data extractor assistant. Your task is to extract all URLs under {topic}'s documentation following these rules:
        - Do NOT include URLs related to Release Notes, REST API or SDK References.
        - Only output URLs inthe same domain as {crawler.url}
        - Avoid duplicated URLs
        - Do NOT provide any comments along with the output
        - It's mandatory to extract the full URL, containing schema (https) and the FQDN, ex: cloud.google.com. 
        - Provide nothing but a list of URLs, enclosed by quotes, and separated by commas
        """
    else:
        prompt = f"""
        You are a data extractor assistant. Your task is to extract all URLs under {prompt}'s documentation following these rules:
        - Do NOT include URLs related to Release Notes, REST API or SDK References.
        - Only output URLs inthe same domain as {crawler.url}
        - Avoid duplicated URLs
        - Do NOT provide any comments along with the output
        - It's mandatory to extract the full URL, containing schema (https) and the FQDN, ex: cloud.google.com. 
        - Provide nothing but a list of URLs, enclosed by quotes, and separated by commas
        """
    logr('Trying to extract the link URLs from the HTML body ...')
    # logr(f"prompt: {prompt}")
    try:
        if model_id.startswith("gemini"):
            result = gemini_inference.run_text_inference(payload, prompt, "string", model_id)
        else:
            result = claude_inference.run_text_inference(payload, prompt, "string", model_id)   
    except Exception as e:
        logr(f"error: failed to generate content - {e}")
        return
    logr(f'result from stage #1 scraper: {result}')
    result = convert_string_to_list(result)
    logr(f'stage #1 scraper has returned {len(result)} URLs')
    time.sleep(3)

    # stage #2 Scraper
    try:
        job_id = create_scrape_job(result, scrapeuse_token, "markdown")
        logr(f"stage #2 job created with ID: {job_id}")
    except Exception as e:
        logr(f"error: Failed to stage #2 scraper job - {e}")
        return
    
    # Check job status
    while True:
        r = get_job_info(job_id, scrapeuse_token)
        status = r["status"]
        logr(f"stage #2 job status: {status}")
        if status == 'succeeded':
            break
        time.sleep(10)

    # Download the content
    output_path = f'{download_folder}/{int(time.time())}-{topic}-scrapejob.md'
    get_scraped_data(job_id, scrapeuse_token, output_path, json_output=True)
    logr(f"stage #2 scraper data downloaded to: {output_path}")

    with open(output_path, "r") as f:
        payload = f.read()
        if model_id.startswith("gemini"):
            r = gemini_inference.count_chars_and_tokens(model_id, payload)
        else:
            r = claude_inference.count_chars_and_tokens(model_id, payload)
        logr(f"characters: {convert_integer_to_decimal(r['num_chars'])}")
        logr(f"tokens: {convert_integer_to_decimal(r['num_tokens'])}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Web Scraper Script")
    parser.add_argument("-u", "--url", type=str, help="URL to scrape")
    parser.add_argument("-p", "--prompt", type=str, default=None, help="Prompt for data extraction")
    parser.add_argument("-t", "--scrapeuse_token", type=str, help="SCRAPEUSE_TOKEN for authentication")
    parser.add_argument("-f", "--folder", type=str, default="/mnt/genai/scraper_downloads",help="Download folder")
    parser.add_argument("-m", "--model", type=str, default="gemini-1.5-flash-001", help="Model for inference")

    args = parser.parse_args()
    main(args.url, args.prompt, args.scrapeuse_token, args.folder, args.model)