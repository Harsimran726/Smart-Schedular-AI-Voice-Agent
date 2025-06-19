from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any
from agent import user_input
import uvicorn 
import json 
from fastapi.responses import HTMLResponse
import os
import edge_tts
import asyncio
import tempfile

app = FastAPI()


origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=['GET','POST'],
    allow_headers=["*"],
    expose_headers=["*"]
)

class ChatRequest(BaseModel):
    message: str  

class TTSRequest(BaseModel):
    text: str

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    try:
        user_message = request.message
        response = user_input(user_message)
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/tts")
async def text_to_speech(request: TTSRequest):
    try:
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_file:
            temp_path = temp_file.name

        # Initialize Edge TTS with a natural voice
        communicate = edge_tts.Communicate(request.text, "en-US-JennyNeural")
        
        # Generate audio file
        await communicate.save(temp_path)

        # Create a generator to stream the file
        def iterfile():
            with open(temp_path, "rb") as f:
                yield from f
            # Clean up the temporary file after streaming
            os.unlink(temp_path)

        # Return the audio file as a streaming response
        return StreamingResponse(
            iterfile(),
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": "attachment;filename=speech.mp3"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/", response_class=HTMLResponse)
async def root():
    with open(os.path.join("templates", "index.html"), "r", encoding="utf-8") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)


