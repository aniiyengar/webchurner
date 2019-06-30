
import requests
import json
from flask import Flask
from flask import request as req
from flask import Response
from churner import churn

app = Flask(__name__)

def request(url):
    return requests.get(
        url,
        headers = { 'User-Agent': 'webchurner' }
    ).text

@app.route('/churn')
def churn_handler():
    url = req.args.get('url')

    if not url:
        return 'Must supply a URL.'

    body = request(url)
    title, date, content = churn(url, body)

    response = Response(
        json.dumps({
            'title': title,
            'date': date,
            'content': content
        })
    )
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Content-Type'] = 'application/json'

    return response

if __name__ == '__main__':
    app.run(port=8000)
