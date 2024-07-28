import requests
import json
import re
import datetime

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

class web_crawler:
    def __init__(self, url, mode="load", endpoint="http://192.168.100.9:3003/navigate", screenshot=False, save_html=False):
        self.url = url
        self.mode = mode
        self.endpoint = endpoint
        self.screenshot = screenshot
        self.save_html = save_html
        self.request = self.process()

    def process(self):
        headers = {
            "Content-Type": "application/json"
        }
        payload = {
            "url": self.url,
            "mode": self.mode,
            "screenshot": self.screenshot,
            "html": self.save_html,
            "full_content" : None
        }

        try:
            response = requests.post(self.endpoint, headers=headers, json=payload)
            response.raise_for_status()  # Raises an HTTPError for bad responses
            if response.status_code == 200:
                self.content = response.json()
            else:
                self.content = {"error": "Failed to process job", "status_code": response.status_code}
        except requests.exceptions.RequestException as e:
            self.content = {"error": f"Connection error: {str(e)}"}
        except json.JSONDecodeError:
            self.content = {"error": "Failed to decode JSON response"}