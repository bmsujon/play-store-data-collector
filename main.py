from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from google_play_scraper import app as gps_app, search as gps_search
from app_store_scraper import AppStore
from typing import List, Dict, Any
import re
import logging
import requests
from bs4 import BeautifulSoup
import urllib.parse
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

fastapi_app = FastAPI(
    title="App Analyzer API",
    description="API for analyzing Android and iOS apps and finding similar apps",
    version="1.0.0"
)

class AppAnalysisRequest(BaseModel):
    android_app_name: str
    url: str

class AppStoreAnalysisRequest(BaseModel):
    ios_app_name: str
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

def extract_app_id(url: str) -> str:
    """Extract app ID from App Store URL."""
    pattern = r'/id(\d+)'
    match = re.search(pattern, url)
    if not match:
        raise HTTPException(status_code=400, detail="Invalid App Store URL")
    return match.group(1)

def get_app_store_data(app_id: str) -> Dict[str, Any]:
    """Get app data directly from App Store webpage."""
    url = f"https://apps.apple.com/us/app/id{app_id}"
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract basic information
        title = soup.find('h1').text.strip() if soup.find('h1') else ""
        developer = soup.find('h2').text.strip() if soup.find('h2') else ""
        description = soup.find('div', {'class': 'section__description'}).text.strip() if soup.find('div', {'class': 'section__description'}) else ""
        
        # Extract rating
        rating_element = soup.find('div', {'class': 'we-rating-count'})
        rating = rating_element.text.strip() if rating_element else "0"
        
        # Extract price
        price_element = soup.find('div', {'class': 'price'})
        price = price_element.text.strip() if price_element else "Free"
        
        return {
            "title": title,
            "developer": developer,
            "description": description,
            "rating": rating,
            "price": price,
            "url": url
        }
    except Exception as e:
        logger.error(f"Error fetching app data: {str(e)}")
        return {}

def search_similar_apps(app_name: str, exclude_app_id: str) -> List[Dict[str, Any]]:
    """Search for similar apps on the App Store."""
    similar_apps = []
    try:
        # Use the App Store's search API with more specific parameters
        search_url = "https://itunes.apple.com/search"
        
        # Add financial-related keywords to improve search relevance
        search_terms = [
            f"{app_name} mobile wallet",
            f"{app_name} payment",
            f"{app_name} financial",
            "mobile wallet payment",
            "digital wallet payment"
        ]
        
        seen_app_ids = set()
        
        for search_term in search_terms:
            if len(similar_apps) >= 10:
                break
                
            params = {
                'term': search_term,
                'country': 'us',
                'entity': 'software',
                'limit': 20,
                'genreId': 6015  # Finance category ID
            }
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'application/json',
            }
            
            response = requests.get(search_url, params=params, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            if 'results' in data:
                for app in data['results']:
                    try:
                        app_id = str(app.get('trackId', ''))
                        if (app_id and 
                            app_id != exclude_app_id and 
                            app_id not in seen_app_ids and
                            len(similar_apps) < 10):
                            
                            # Check if the app is relevant (contains keywords in title or description)
                            title = app.get('trackName', '').lower()
                            description = app.get('description', '').lower()
                            keywords = ['wallet', 'payment', 'bank', 'money', 'transfer', 'financial']
                            
                            if any(keyword in title.lower() or keyword in description.lower() for keyword in keywords):
                                app_data = {
                                    "appId": app_id,
                                    "title": app.get('trackName', ''),
                                    "developer": app.get('sellerName', ''),
                                    "description": app.get('description', ''),
                                    "price": app.get('formattedPrice', 'Free'),
                                    "rating": str(app.get('averageUserRating', '0')),
                                    "rating_count": str(app.get('userRatingCount', '0')),
                                    "url": app.get('trackViewUrl', ''),
                                    "category": app.get('primaryGenreName', '')
                                }
                                similar_apps.append(app_data)
                                seen_app_ids.add(app_id)
                    except Exception as e:
                        logger.warning(f"Error processing similar app: {str(e)}")
                        continue
                        
    except Exception as e:
        logger.error(f"Error searching for similar apps: {str(e)}")
    
    return similar_apps

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
        similar_apps = gps_search(
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
        logger.error(f"Error analyzing Android app: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@fastapi_app.post("/analyze-ios-app", response_model=AppAnalysisResponse)
async def analyze_ios_app(request: AppStoreAnalysisRequest):
    try:
        # Extract app ID from URL
        app_id = extract_app_id(request.url)
        logger.info(f"Analyzing iOS app: {request.ios_app_name} (ID: {app_id})")
        
        # Get target app details
        try:
            # Get basic app data from webpage
            app_data = get_app_store_data(app_id)
            
            # Get reviews using AppStore scraper
            target_app_scraper = AppStore(country="us", app_name=request.ios_app_name, app_id=app_id)
            try:
                target_app_scraper.review()
                reviews = getattr(target_app_scraper, "reviews", [])[:10]
            except Exception as e:
                logger.warning(f"Could not fetch reviews: {str(e)}")
                reviews = []
            
            # Combine data
            target_app = {
                "appId": app_id,
                "title": app_data.get("title", request.ios_app_name),
                "description": app_data.get("description", ""),
                "developer": app_data.get("developer", ""),
                "price": app_data.get("price", ""),
                "rating": app_data.get("rating", ""),
                "url": app_data.get("url", ""),
                "reviews": reviews
            }
        except Exception as e:
            logger.error(f"Error scraping target app: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error scraping target app: {str(e)}")
        
        # Search for similar apps
        similar_apps = search_similar_apps(request.ios_app_name, app_id)
        
        return AppAnalysisResponse(
            target_app=target_app,
            similar_apps=similar_apps
        )
        
    except Exception as e:
        logger.error(f"Error analyzing iOS app: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(fastapi_app, host="0.0.0.0", port=8000) 