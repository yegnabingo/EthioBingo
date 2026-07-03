# app/main.py
# Placeholder for EthioBingo FastAPI entrypoint

from fastapi import FastAPI

app = FastAPI()

@app.get('/')
async def root():
    return {"message": "EthioBingo placeholder"}

if __name__ == '__main__':
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000)
