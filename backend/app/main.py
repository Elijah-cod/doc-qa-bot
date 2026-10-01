from fastapi import FastAPI

app = FastAPI(title="Doc Q&A Bot")

@app.get("/health")
def health():
    return {"ok": True}
