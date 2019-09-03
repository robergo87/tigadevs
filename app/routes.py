from app import app
from flask import render_template,request
from .trendsapi import obtain_keyword_trends
import json

@app.route("/")
@app.route("/index")
def keyword():
    return render_template("keyword.html",keyword="python")
    
@app.route("/get")
def load_keyword():
    keyword = request.args.get('keyword',default='python',type = str)
    country = request.args.get('country',default='US',type = str)
    answer = obtain_keyword_trends(keyword,country)
    if answer[0]:
        for kw in answer[1]:
            return json.dumps({
                "status": "success",
                "data": {"listing": answer[1][kw],"keyword": keyword}
            })
    else:
        return json.dumps({
            "status": "error",
            "data": answer[1:]
        })