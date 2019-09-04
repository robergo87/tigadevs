"""
Main routes of Trends App
"""
import json
from flask import render_template, request
from app import app
from .trendsapi import TrendsAPISession, TrendsAPIError

@app.route("/")
@app.route("/index")
def home():
    """ home page static view """
    return render_template("keyword.html", keyword="python")

@app.route("/get")
def load_keyword():
    """ ajax method for obtaining keyword data """
    keyword = request.args.get('keyword', default='python', type=str)
    country = request.args.get('country', default='US', type=str)
    try:
        api_session = TrendsAPISession()
        api_result = api_session.get_trends(keyword, country)
        return json.dumps({
            "status": "success",
            "data": {
                "listing": api_result[list(api_result.keys())[0]],
                "keyword": keyword
            }
        })
    except TrendsAPIError as err:
        return json.dumps({
            "status": "error",
            "message": str(err),
            "data": err.error
        })
