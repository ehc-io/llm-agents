import requests
import time
import re
import argparse
import os
from bs4 import BeautifulSoup
from IPython.display import Markdown, display

# My modules
import gemini_inference, claude_inference
from shared import web_crawler
from shared import log_message as logr

class SearchResult:
    def __init__(self, json_data, question, llm_model, verbose=False):
        self.json_data = json_data
        self.question = question
        self.llm_model = llm_model
        self.verbose = verbose
        self.title = None
        self.link = None
        self.raw_content = None
        self.markdown = None
        self.relevance = None
        self.extract_search_info()
        
    def to_string(self):
        return (
            f"Title: {self.title}\n\n"
            f"Content: {self.markdown}\n\n"
            f"URL: {self.link}\n\n"
            f"Relevance: {self.relevance}\n"
        )
             
    def extract_search_info(self):
        if isinstance(self.json_data, dict):
            # Handle single dictionary input
            self._process_single_result(self.json_data)
        elif isinstance(self.json_data, list):
            # Handle list of dictionaries input
            if self.json_data:
                self._process_single_result(self.json_data[0])
        else:
            # Handle unexpected input type
            raise ValueError("Input must be a dictionary or a list of dictionaries")

    def _process_single_result(self, item):
        self.title = item.get('title', '')
        self.link = item.get('link', '')
        if self.link:
            try:
                self.raw_content = self.fetch_raw_content(self.link)
                self.markdown = self.convert_to_markdown(self.raw_content)
                self.relevance = self.evaluate_relevance(self.markdown, self.question, self.llm_model)
            except Exception as e:
                logr(f"Error processing result for link {self.link}: {e}")

    def fetch_raw_content(self, url):
        logr(f"fetching raw content for: {url}")
        try:
            return web_crawler(url).content["html_body"]
        except Exception as e:
            logr(f"Failed to fetch raw content for {url}: {e}")
            return None

    def convert_to_markdown(self, raw_content):
        logr("Converting raw HTML to markdown")
        try:
            start_time = time.time()
            # m = html2markdown2(raw_content, self.llm_model)
            m = html2markdown(raw_content)
            del self.raw_content
            end_time = time.time()
            if self.verbose:
                logr(f"convert_to_markdown execution time: {round(end_time - start_time, 5)} seconds")
            return m
        except Exception as e:
            logr(f"Failed to convert raw content to markdown: {e}")
            return None

    def evaluate_relevance(self, markdown, question, llm_model):
        try:
            logr(f"evaluating the relevance of the content scraped ...")
            start_time = time.time()
            PROMPT = f"""
                You are an advanced AI assistant specialized in analyzing web search results. Please perform the following tasks:

                1. Make sense of all the information provided. Ingest the data thoughtfully and make your own conclusions.

                2. Provide a concise and blunt review of the content provided

                3. Relevance score:
                Assign a relevance score from 1 to 5 (where 1 is least relevant and 5 is most relevant). Provide a score based on how relevant is the content related to the user's question: {question}.

                4. Format your output as follows:
                    evaluation : <Direct and blunt review of the content>,
                    score : <relevance Score [1-5]>
                5. Do NOT output nothing but the json as instructed.
                6. Remember to base your responses solely on the provided data and maintain a neutral, informative tone.
            """
            if llm_model.startswith("gemini"):
                content_check = gemini_inference.run_inference(markdown, PROMPT, "string", llm_model)
            else:
                content_check = claude_inference.run_inference(markdown, PROMPT, "string", llm_model)
            end_time = time.time()
            if self.verbose:
                logr(f"evaluate_relevance execution time: {round(end_time - start_time, 5)} seconds")
            return content_check
        except Exception as e:
            logr(f"Failed to evaluate relevance: {e}")
            return None

def llm_based_html2markdown(html, model_id):
    HTML_BODY_EXTRACTOR_PROMPT = """
        You are an expert HTML parser and markdown converter. Your task is to take raw HTML code as input, extract only the relevant content from the HTML body, and convert it to markdown format. Follow these steps:
        1. Parse the input HTML code.
        2. Identify and extract the content within the <body> tags.
        3. Remove any unnecessary HTML elements, such as <script>, <style>, or <header> tags.
        4. Convert the remaining HTML elements to their markdown equivalents:
        - Convert headings (<h1>, <h2>, etc.) to markdown headings (# , ##, etc.)
        - Convert <p> tags to plain text paragraphs
        - Convert <a> tags to markdown links [text](url)
        - Convert <img> tags to markdown images ![alt text](image url)
        - Convert <ul> and <ol> lists to markdown lists (- or 1., 2., etc.)
        - Convert <strong> or <b> tags to **bold text**
        - Convert <em> or <i> tags to *italic text*
        - Convert <code> tags to `inline code`
        - Convert <pre> tags to ```code blocks```
        5. Do not output any comments, just plain markdown related to the content
        6. Preserve the overall structure and hierarchy of the content.
        7. Output the resulting markdown-formatted text.
    """
    if model_id.startswith("gemini"):
        markdown = gemini_inference.run_inference(html, HTML_BODY_EXTRACTOR_PROMPT, "string", model_id)
    else:
        markdown = claude_inference.run_inference(html, HTML_BODY_EXTRACTOR_PROMPT, "string", model_id)
    return markdown

def html2markdown(html):
    soup = BeautifulSoup(html, 'html.parser')
    # Remove unnecessary elements
    for element in soup(['script', 'style', 'header', 'footer', 'nav']):
        element.decompose()
    body = soup.body if soup.body else soup
    def convert_element(element):
        if element.name is None:
            return element.string
        if element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            return f"{'#' * int(element.name[1])} {element.get_text().strip()}\n\n"
        if element.name == 'p':
            return f"{element.get_text().strip()}\n\n"
        if element.name == 'a':
            return f"[{element.get_text()}]({element.get('href', '')})"
        if element.name == 'img':
            return f"![{element.get('alt', '')}]({element.get('src', '')})"
        if element.name in ['ul', 'ol']:
            items = []
            for i, li in enumerate(element.find_all('li', recursive=False)):
                prefix = '- ' if element.name == 'ul' else f"{i+1}. "
                items.append(f"{prefix}{convert_element(li).strip()}")
            return '\n'.join(items) + '\n\n'
        if element.name in ['strong', 'b']:
            return f"**{element.get_text()}**"
        if element.name in ['em', 'i']:
            return f"*{element.get_text()}*"
        if element.name == 'code':
            return f"`{element.get_text()}`"
        if element.name == 'pre':
            return f"```\n{element.get_text()}\n```\n\n"
        return ''.join(convert_element(child) for child in element.children)
    markdown = convert_element(body)
    # Clean up extra newlines
    markdown = re.sub(r'\n{3,}', '\n\n', markdown)
    return markdown.strip()

def get_search_query(question, model_id):
    logr(f"Generating Google Search Query for: {question}")
    PROMPT = f"""
    You are very creative and sharp. You have mastered the skills related to finding information on the web, knowing every trick to get relevant results from Google search. Your task is to provide the best search query to submit on Google Search to obtain the most relevant results for this question: {question}. Output only the search query. Do not include line breaks, quotes, or any comments.
    """
    search_string = gemini_inference.run_inference(question, PROMPT, 'string', model_id)
    return search_string

def google_search(query, api_key, cx, num_results, start_index, date_restrict='y2'):
    logr(f"Obtaining search results for: {query}")
    base_url = "https://www.googleapis.com/customsearch/v1"

    results = []

    while len(results) < num_results:
        params = {
            'q': query,
            'key': api_key,
            'cx': cx,
            'num': min(10, num_results - len(results)),  # API allows max 10 results per request
            'start': start_index,
            'dateRestrict' : date_restrict
        }

        try:
            response = requests.get(base_url, params=params)
            response.raise_for_status()
            data = response.json()

            if 'items' in data:
                results.extend(data['items'])
                start_index += len(data['items'])
            else:
                break  # No more results

        except requests.exceptions.RequestException as e:
            logr(f"An error occurred: {e}")
            break

    return results[:num_results]

def validate_date_restrict(value):
    pattern = r'^([dhwm]\d+|y[1-3])$'
    if not re.match(pattern, value):
        raise argparse.ArgumentTypeError('Invalid date_restrict format. Must be d[number], w[number], m[number], or y[1-3].')
    return value

def serialize_search_results(search_results):
    return "\n".join([result.to_string() for result in search_results])       

def summarize_results(html_payload, question, model_id, chat_history):
    PROMPT = f"""
        You are an advanced AI assistant specialized in analyzing web search results. Please perform the following tasks:

        1. You're going to be exposed to a series of web search results, supposedly relevant to the question described as follows. having that in mind, make sense of all the information provided to you. Ingest all that data carefully and make your own conclusions.
        
        2. Include Chat History as part of the context if it does make sense.

        3. Once you're done ingesting, provide a through answer. Focus on the main ideas and key points related to the user's query: {question}. When possible, provide examples. If the question is related to coding, provide code snippets.

        4. You can use the knowledge obtained by analyzing the information provided to craft an answer doing some assumptions as long as you are based on facts.

        5. Provide relevant URLs (exclusively extraced from the data provided to you) as reference for further reading. Take into consideration only URLs when the associated score is above 3.

        [CHAT HISTORY]
        {chat_history}
        
        Format your response as follows:
        
        [Your direct answer to the user's question based on the search results]

        References:
        [URLs relevant to the question]
        
        Remember to base your responses solely on the provided data and maintain a neutral, informative tone. Output in markdown format.
    """
    logr(f"PROMPT: {PROMPT}")
    if model_id.startswith("gemini"):
        search_result_analysis = gemini_inference.run_inference(html_payload, PROMPT, 'string', model_id)
    else:
        search_result_analysis = claude_inference.run_inference(html_payload, PROMPT, 'string', model_id)

    return search_result_analysis

def gennie_answer(question, model_id, num_results, start_index, date_restrict, chat_history):
    query = get_search_query(question, 'gemini-1.5-flash-001') # Query improvement only run on gemini flash
    GOOGLE_SEARCH_API_KEY = os.getenv("GOOGLE_SEARCH_API_KEY")
    SEARCH_ENGINE_ID = os.getenv("SEARCH_ENGINE_ID")
    json_data = google_search(query, GOOGLE_SEARCH_API_KEY, SEARCH_ENGINE_ID, num_results=num_results, start_index=start_index, date_restrict=date_restrict)
    logr(f'Google search has brought to you {len(json_data)} results')
    search_results = []
    for json_item in json_data:
        try:
            s = SearchResult(json_item, question, model_id, True)
            search_results.append(s)
        except:
            logr(f'error while trying to process: {s.link}')
    
    payload = serialize_search_results(search_results)
    answer = summarize_results(payload, question, model_id, chat_history)
    return answer

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Web search and analysis tool")
    parser.add_argument("--question", type=str, default=None, required=True, help="The question to search for")
    parser.add_argument("--model_id", type=str, default="gemini-1.5-flash-001", help="Model ID for inference")
    parser.add_argument("--num_results", type=int, default=5, help="Number of search results to return")
    parser.add_argument("--start_index", type=int, default=1, help="Start index for search results")
    parser.add_argument("--date_restrict", type=validate_date_restrict, default="y2", 
                        help="Date restrict parameter for search results (e.g., 'd5', 'w2', 'm6', 'y1')")
    parser.add_argument("--chat_history", type=str, default=None, help="Chat History to be included in the summarization")
    args = parser.parse_args()
    model_id = args.model_id
    question = args.question
    num_results = args.num_results
    start_index = args.start_index
    date_restrict = args.date_restrict
    chat_history = args.chat_history
    
    answer = gennie_answer(question, model_id, num_results, start_index, date_restrict, chat_history)
    print(answer)

