from fastapi import FastAPI
from pydantic import BaseModel
from typing import Dict
import uvicorn

from rag import init_video,ask

app=FastAPI()

class VideoRequest(BaseModel):
    video_id:str 

class ChatRequest(BaseModel):
    video_id:str 
    query:str 

@app.get("/")
def root():
    return {"message":"Youtube Rage API Running"}

@app.post("/init_video")
def initialize_video(req:VideoRequest):
    try:
        result=init_video(req.video_id)
        if isinstance(result,str):
           return {
            "status":"error",
            "message":result
        }
        return {
        "status":"success",
        "video_id":req.video_id
    }
    except Exception as e:
        return {
            "status":"error",
            "message":str(e)
        }




@app.post("/chat")
def chat(req:ChatRequest):
    try:
        response = ask(req.query, req.video_id)

        print("DEBUG RESPONSE:", response)   # 👈 ADD THIS

        if response is None:
            return {
                "status": "error",
                "message": "Model returned None"
            }

        return {
            "status":"success",
            "response":response
        }

    except Exception as e:
        return {
            "status":"error",
            "message":str(e)
        }
if __name__=="__main__":
    uvicorn.run(app, host="0.0.0.0", port=9999)