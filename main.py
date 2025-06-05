from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from google_play_scraper import app as gps_app, search
from typing import List, Dict, Any
import re

fastapi_app = FastAPI(
    title="App Analyzer API",
    description="API for analyzing Android apps and finding similar apps",
    version="1.0.0"
)

class AppAnalysisRequest(BaseModel):
    android_app_name: str
    url: str

class AppAnalysisResponse(BaseModel):
    target_app: Dict[str, Any]
    similar_apps: List[Dict[str, Any]]

def extract_package_name(url: str) -> str:
    """Extract package name from Google Play Store URL."""
    pattern = r'id=([^&]+)'
    match = re.search(pattern, url)
    if not match:
        raise HTTPException(status_code=400, detail="Invalid Google Play Store URL")
    return match.group(1)

@fastapi_app.post("/analyze-app", response_model=AppAnalysisResponse)
async def analyze_app(request: AppAnalysisRequest):
    try:
        # Extract package name from URL
        package_name = extract_package_name(request.url)
        
        # Get target app details
        target_app = gps_app(
            package_name,
            lang='en',
            country='us'
        )
        
        # Search for similar apps
        similar_apps = search(
            request.android_app_name,
            lang='en',
            country='us',
            n_hits=10
        )
        
        # Get detailed information for similar apps
        detailed_similar_apps = []
        for app_data in similar_apps:
            try:
                detailed_app = gps_app(
                    app_data['appId'],
                    lang='en',
                    country='us'
                )
                detailed_similar_apps.append(detailed_app)
            except Exception as e:
                continue
        
        return AppAnalysisResponse(
            target_app=target_app,
            similar_apps=detailed_similar_apps
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(fastapi_app, host="0.0.0.0", port=8000) 