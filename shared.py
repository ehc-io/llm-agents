import requests
import json
import re
import datetime
import os
from bs4 import BeautifulSoup

def ensure_folder(folder_path):
  """
  Checks if a folder exists and creates it if it doesn't.

  Args:
    folder_path (str): The path to the folder.

  Returns:
    bool: True if the folder exists or was created successfully, False otherwise.
  """
  if not os.path.exists(folder_path):
    try:
      os.makedirs(folder_path)
      print(f"Folder created: {folder_path}")
    except OSError as e:
      print(f"Error creating folder: {e}")
      return False
  return True

def log_message(message):
  """Logs a message with a timestamp.

  Args:
    message: The message to log.
  """
  timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
  print(f'[{timestamp}] {message}')

def convert_integer_to_decimal(number):
    number_str = str(number)
    formatted_number = re.sub(r'(?<=\d)(?=(\d{3})+$)', '.', number_str)
    return formatted_number

def convert_string_to_list(url_string):
    return [url.strip().strip('"') for url in url_string.split(',')]

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
  
class scraper_api:
    def __init__(self, url , outputMode="raw-html", pageLoadTimeout=0, structured=False, sessionStateFolder="session-data/tmp", mode="full-body-load", selector=False, endpoint="http://192.168.100.9:3002/navigate", screenshot=False, save_html=False, sessionState_enable=False):
        self.url = url
        self.mode = mode
        self.selector = selector
        self.endpoint = endpoint
        self.screenshot = screenshot
        self.save_html = save_html
        self.sessionState_enable = sessionState_enable
        self.sessionStateFolder = sessionStateFolder
        self.outputMode=outputMode
        self.structuredOutput=structured
        self.pageLoadTimeout=pageLoadTimeout
        self.request = self.process()

    def process(self):
        headers = {
            "Content-Type": "application/json"
        }
        payload = {
            "url": self.url,
            "mode": self.mode,
            "selector": self.selector,
            "screenshot": self.screenshot,
            "save_html": self.save_html,
            "sessionState_enable": self.sessionState_enable,
            "sessionStateFolder": self.sessionStateFolder,
            "outputMode": self.outputMode,
            "structuredOutput": self.structuredOutput,
            "pageLoadTimeout": self.pageLoadTimeout
        }
        try:
            response = requests.post(self.endpoint, headers=headers, json=payload)
            # response.raise_for_status()  # Raises an HTTPError for bad responses
            if response.status_code == 200:
                self.content = response.content
                # if  self.structuredOutput:
                #     self.content = json.loads(response.content)
                # else:
                #     self.content = response.content
            else:
                self.content = {"error": "Failed to process job", "status_code": response.status_code}
        except requests.exceptions.RequestException as e:
            self.content = {"error": f"Connection error: {str(e)}"}