import argparse
import json
import requests
import os
import time

def read_file_lines(file_path):
    with open(file_path, 'r') as file:
        lines = [line.strip() for line in file if line.strip()]
    return lines

def log_message(message):
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())
    print(f"[{int(time.time())}.{timestamp}] {message}")
    
def create_scrape_job(urls, token, output_format):
    api_url = "https://api.usescraper.com/crawler/jobs"
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    payload = {
        "urls": urls,
        "exclude_globs": [],
        "exclude_elements": """nav, header, footer, script, style, noscript, svg, [role="alert"], [role="banner"], [role="dialog"], [role="alertdialog"], [role="region"][aria-label*="skip" i], [aria-modal="true"]""",
        "output_format": output_format,
        "output_expiry": 604800,
        "page_limit": 100,
        "force_crawling_mode": "link",
        "block_resources": True,
        "include_linked_files": False
    }
    response = requests.post(api_url, headers=headers, data=json.dumps(payload))
    time.sleep(3)
    if response.status_code >= 200:
        result = response.json()
        # print(result)
        log_message(f"Crawl job created with ID: {result['id']}")
        log_message(f"Status: {result['status']}")
        return result['id']
    else:
        log_message(f"Error: {response.status_code} - {response.text}")
        return None

def get_job_info(job_id, token):
    api_url = f"https://api.usescraper.com/crawler/jobs/{job_id}"
    headers = {
        'Authorization': f'Bearer {token}'
    }
    response = requests.get(api_url, headers=headers)
    if response.status_code == 200:
        result = response.json()
        # log_message(f"Job Info: {json.dumps(result, indent=2)}")
        return result
    else:
        log_message(f"Error: {response.status_code} - {response.text}")
        return None

def get_scraped_data(job_id, token, output_path, json_output=False):
    api_url = f"https://api.usescraper.com/crawler/jobs/{job_id}/data"
    headers = {
        'Authorization': f'Bearer {token}'
    }
    response = requests.get(api_url, headers=headers)
    if response.status_code == 200:
        result = response.json()
        if json_output:
            parsed_data = []
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            f = open(output_path, 'a')
            for item in result.get('data', []):
                f.write(item.get('text', {}) + "\n\n")
            log_message(f"Scraped data saved to: {output_path}")
            f.close()
        else:
            json.dumps(result, indent=2)
    
    else:
        log_message(f"Error: {response.status_code} - {response.text}")
        
def main():
    parser = argparse.ArgumentParser(description='Crawl URLs using the Scraper API')
    parser.add_argument('--url_file', '-u', help='Text file containing URLs to crawl')
    parser.add_argument('--output_format', '-o', default='markdown', choices=['text', 'html', 'markdown'], help='Output format for crawled content')
    parser.add_argument('--token', '-t', required=True, help='API authentication token')
    parser.add_argument('--job_id', '-j', help='Job ID to get info or data')
    parser.add_argument('--action', '-a', choices=['create', 'info', 'data'], required=True, help='Action to perform: create, info, data')
    parser.add_argument('--parse', '-p', action='store_true', help='Parse JSON data')
    parser.add_argument('--output_path', '-op', default=f'/mnt/genai/scraper_downloads/{int(time.time())}-scrapejob.md',
                        help='Path to save the scraped data')
    args = parser.parse_args()

    if args.action == 'create':
        urls = read_file_lines(args.url_file)
        create_scrape_job(urls, args.token, args.output_format)
    elif args.action == 'info':
        get_job_info(args.job_id, args.token)
    elif args.action == 'data':
        get_scraped_data(args.job_id, args.token, args.output_path, args.parse)

if __name__ == '__main__':
    main()