import time
from gemini_inference import count_chars_and_tokens, run_inference
from usescraper_wrapper import create_scrape_job, get_job_info, get_scraped_data
from shared import log_message, web_crawler, convert_integer_to_decimal, convert_string_to_list

def main(url, prompt, scrapeuse_token, download_folder):
    # stage #1 Scraper
    log_message(f"starting stage #1 scraper")
    crawler = web_crawler(url=url)

    if "error" in crawler.content:
        error_message = crawler.content["error"]
        if "Connection error" in error_message:
            log_message(f"Crawling failed due to connection issues: {error_message}")
        elif "Failed to decode JSON response" in error_message:
            log_message(f"Crawling failed due to JSON decoding error: {error_message}")
        else:
            log_message(f"Crawling failed: {error_message}")
        return False

    if "html_body" not in crawler.content:
        log_message("error: HTML body not found in the result.")
        return

    topic = crawler.url.split('/')[3]
    payload = crawler.content["html_body"]
    if prompt is None:
        prompt = f"You are a data extractor assistant. \nYour task is to extract all URLs under {topic}'s documentation following these rules:\n0. Do NOT include URLs related to Release Notes, REST API or SDK References.\n1. Only output URLs inthe same domain as {job.url}.\n2. Avoid duplicated URLs.\n3. Do NOT provide any comments along with the output.\n4. It's mandatory to extract the full URL, containing schema (https) and the FQDN, ex: cloud.google.com \n5. Provide nothing but a list of URLs, enclosed by quotes, and separated by commas"
    else:
        prompt = f"You are a data extractor assistant. \nYour task is to extract all URLs related to the following topic: {prompt} from the scraped data provided. To accomplish that please follow these rules:\n1. Do NOT include URLs related to Release Notes, REST API or SDK References.\n2. Avoid duplicated URLs.\n3. Do NOT provide any comments along with the output.\n4. It's mandatory to extract the full URL, containing schema (https) and the FQDN, ex: cloud.google.com \n5. Provide nothing but a list of URLs, enclosed by quotes, and separated by commas"
    log_message('Tring to extract the link URLs from the HTML body ...')
    # log_message(f"prompt: {prompt}")
    try:
        result = run_inference(payload, prompt, "string", "gemini-1.5-pro-001")
    except Exception as e:
        log_message(f"error: failed to generate content - {e}")
        return
    log_message(f'result from stage #1 scraper: {result}')
    result = convert_string_to_list(result)
    log_message(f'stage #1 scraper has returned {len(result)} URLs')
    time.sleep(5)

    # stage #2 Scraper
    try:
        job_id = create_scrape_job(result, scrapeuse_token, "markdown")
        log_message(f"stage #2 job created with ID: {job_id}")
    except Exception as e:
        log_message(f"error: Failed to stage #2 scraper job - {e}")
        return
    
    # Check job status
    while True:
        r = get_job_info(job_id, scrapeuse_token)
        status = r["status"]
        log_message(f"stage #2 job status: {status}")
        if status == 'succeeded':
            break
        time.sleep(10)

    # Download the content
    output_path = f'{download_folder}/{int(time.time())}-{topic}-scrapejob.md'
    get_scraped_data(job_id, scrapeuse_token, output_path, json_output=True)
    log_message(f"stage #2 scraper data downloaded to: {output_path}")

    with open(output_path, "r") as f:
        payload = f.read()
        c, t = count_chars_and_tokens("gemini-1.5-flash-001", payload)
    log_message(f"characters: {convert_integer_to_decimal(c)}")
    log_message(f"tokens: {convert_integer_to_decimal(t.total_tokens)}")
    log_message(f"billable chars: {convert_integer_to_decimal(t.total_billable_characters)}")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Web Scraper Script")
    parser.add_argument("-u", "--url", type=str, help="URL to scrape")
    parser.add_argument("-p", "--prompt", type=str, default=None, help="Prompt for data extraction")
    parser.add_argument("-t", "--scrapeuse_token", type=str, help="SCRAPEUSE_TOKEN for authentication")
    parser.add_argument("-f", "--folder", type=str, default="/mnt/genai/scraper_downloads",help="Download folder")

    args = parser.parse_args()
    main(args.url, args.prompt, args.scrapeuse_token, args.folder)