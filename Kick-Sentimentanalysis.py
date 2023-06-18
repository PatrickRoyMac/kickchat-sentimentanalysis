from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import json
import re
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from flask import Flask, render_template, request

# Configure Chrome options
chrome_options = Options()
chrome_options.add_argument("--headless")  # Run Chrome in headless mode
chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/114.0") # set this to what ever useragent you want - I found that this worked for me

# Set the path to the ChromeDriver executable
# This needs to be set to your ChromeDriver Executable Path
chromedriver_path = r'******'

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    channel = request.form.get('search')  # Get the channel from the search input

    if not channel:
        return render_template('index.html')

    channel_url = f'https://kick.com/api/v2/channels/{channel}'

    def get_channel_id():
        driver = webdriver.Chrome(executable_path=chromedriver_path, options=chrome_options)
        driver.get(channel_url)
        driver.implicitly_wait(2)
        channel_id_page_source = driver.page_source
        response_string_channel_id = channel_id_page_source
        json_string_channel_id = re.sub('<.*?>', '', response_string_channel_id)
        channel_id_load = json.loads(json_string_channel_id)
        driver.quit()
        return channel_id_load['id']
    

    # Get the channel ID
    channel_id = get_channel_id()

    chat_url = f'https://kick.com/api/v2/channels/{channel_id}/messages'

    def get_chat_data():
        chat_data = []
        num_requests = 2
        for _ in range(num_requests):
            driver = webdriver.Chrome(executable_path=chromedriver_path, options=chrome_options)
            driver.get(chat_url)
            driver.implicitly_wait(5)
            chat_data_page_source = driver.page_source
            response_string_chat_data = re.sub('<.*?>', '', chat_data_page_source)
            chat_data_page = json.loads(response_string_chat_data)
            messages = chat_data_page['data']['messages']
            chat_data.extend(messages)
            driver.quit()

        # Deduplicate chat messages based on content
        deduplicated_chat_data = {message['content']: message for message in chat_data}.values()
        contents = [message['content'] for message in deduplicated_chat_data]
        return contents

    # Get the chat data
    chat_contents = get_chat_data()

    # Create an instance of the SentimentIntensityAnalyzer
    analyzer = SentimentIntensityAnalyzer()

    # Variables to keep track of sentiment counts
    positive_count = 0
    negative_count = 0
    neutral_count = 0
    total_count = len(chat_contents)  # Total number of chat messages

    # Perform sentiment analysis on each chat message
    for content in chat_contents:
        # Get the sentiment scores
        scores = analyzer.polarity_scores(content)

        # Interpret the sentiment scores
        if scores['compound'] >= 0.05:
            positive_count += 1
        elif scores['compound'] <= -0.05:
            negative_count += 1
        else:
            neutral_count += 1

    # Calculate the percentage of each sentiment
    positive_percentage = (positive_count / total_count) * 100
    negative_percentage = (negative_count / total_count) * 100
    neutral_percentage = (neutral_count / total_count) * 100

    # Return the sentiment analysis results
    return render_template('results.html', total_count=total_count,
                           positive_percentage=positive_percentage,
                           negative_percentage=negative_percentage,
                           neutral_percentage=neutral_percentage,
                           channel_name=channel)

if __name__ == '__main__':
    app.run(debug=True)
