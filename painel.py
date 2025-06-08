from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import json

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def painel(request: Request):
    try:
        with open("sinais.json") as f:
            sinais = json.load(f)[-20:]
    except:
        sinais = []
    return templates.TemplateResponse("painel.html", {"request": request, "sinais": sinais})

async def iniciar_painel():
    import uvicorn
    config = uvicorn.Config("painel:app", host="0.0.0.0", port=8080, reload=False)
    server = uvicorn.Server(config)
    await server.serve()
