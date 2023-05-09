from flask import Flask, render_template, request, jsonify, redirect

import os
import glob
import openai
import requests
from dotenv import load_dotenv
from bs4 import BeautifulSoup

load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/submit', methods=['POST'])
def submit():
    input_url = request.json['input']
    print(f"Received input: {input_url}")

    # Download HTML and all Images
    r = requests.get(input_url, allow_redirects=True)
    # Parse the HTML content using BeautifulSoup
    soup = BeautifulSoup(r.content, 'html.parser')
    # Find all image tags in the HTML content
    image_tags = soup.find_all('img')
    # Download each image and save it to the images directory
    for img in image_tags:
        img_url = img['src']
        img_name = img_url.split('/')[-1]
        img_data = requests.get(input_url + '/' + img_url).content
        with open('static/'+img_name, 'wb') as f:
            f.write(img_data)
    with open('temp.html', 'w') as f:
        f.truncate()
        f.write(str(soup))

    string_content = r.content.decode('utf-8')

    initial_prompt = """
    You are an accessibility expert at Twitter where you work on making the website more accessible to people with visual disorders.
    I'm going to pass in an HTML file to you that is not optimised for people with visual disabilities and your job is to create an equivalent HTML file for people with the visual disorders.
    Create an alternate HTML file and include comments in the HTML file wherever you make changes. Make sure to preserve the original positioning of elements in the HTML page like whitespaces and tables.
    Definitely make the following changes - contrast ratio between text and its background should be at least 4.5:1 for normal text and 3:1 for large text (18pt or 14pt bold).
    Make sure to remove any background images, use a light background and a high contrast between text and background. Further, generic generic alt text fields for all images.
    """

    messages = [{"role": "system", "content": initial_prompt}, {"role": "user", "content": string_content}]
    print("making api request to openai, this can take a few minutes!...")
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages= messages,
        temperature=1,
        top_p=1,
        frequency_penalty=0.0,
        presence_penalty=0.0,
    )

    # Open our target HTML file in write mode
    with open('templates/landing.html', 'w') as html_file:
        # Truncate contents because we'll be writing a fresh response file from GPT4
        html_file.truncate()
        # response from GPT4
        edited_html = response["choices"][0]["message"]["content"]
        # its a little tricky to serve this new HTML file with all its image contents
        # so we are editing the IMG tags to ensure we can serve all images on the page from the static/ folder
        edited_soup = BeautifulSoup(edited_html, 'html.parser')
        # Find all image tags in the HTML content
        image_tags = edited_soup.find_all('img')
        # modify the image URL in each of them to get the static file serving format working with Flask
        for img in image_tags:
            img_url = img['src']
            img['src'] = "{{url_for('static', filename='" + img_url + "')}}"

        # Write the new HTML code to the file
        html_file.write(str(edited_soup))

    print("successfully edited HTML page, navigate to /render to view the new page!")

@app.route('/render')
def render():
    return render_template('landing.html')

if __name__ == '__main__':
    app.run(debug=True)