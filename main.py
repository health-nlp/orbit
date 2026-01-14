from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def home():
    return {"message": "API works! Import deactivated."}

@app.get("/test")
def test(): 
    return "This is a text without anything else (TEST)"