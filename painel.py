from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import json
import os

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def exibir_painel(request: Request):
    sinais = []
    try:
        with open("logs/sinais.jsonl", "r", encoding="utf-8") as f:
            for linha in f.readlines()[-20:]:
                sinais.append(json.loads(linha))
    except:
        pass
    sinais.reverse()
    return templates.TemplateResponse("painel.html", {
        "request": request,
        "sinais": sinais,
        "chart_url": "/static/chart.png",
        "banner_link": "https://bit.ly/449TH4F",
        "banner_img": "https://i.ibb.co/ZcK9dcT/banner.png"
    })
