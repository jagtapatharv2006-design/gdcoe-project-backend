"""
Web scrapers for fetching competitive programming ratings.
Supports Codeforces and LeetCode.
"""

import os
import re
import time
from typing import Optional, Dict
import requests
from config import Config
from logger import logger


def fetch_codeforces_rating(username: str) -> Optional[float]:
    """
    Fetch Codeforces rating from API.
    
    Args:
        username: Codeforces username
        
    Returns:
        Rating as float or None if failed
    """
    if not username or not isinstance(username, str):
        return None
    
    username = username.strip()
    if not username:
        return None
    
    try:
        url = f"https://codeforces.com/api/user.info?handles={username}"
        
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get("status") == "OK" and "result" in data:
            users = data["result"]
            if users and len(users) > 0:
                user_info = users[0]
                rating = user_info.get("rating")
                
                if rating is not None:
                    rating_float = float(rating)
                    logger.info(f"Fetched CF rating for {username}: {rating_float}")
                    return rating_float
        
        logger.warning(f"No rating found for Codeforces user: {username}")
        return None
        
    except requests.exceptions.Timeout:
        logger.warning(f"Timeout fetching Codeforces rating for {username}")
        return None
    except requests.exceptions.RequestException as e:
        logger.warning(f"Error fetching Codeforces rating: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error fetching Codeforces rating: {str(e)}")
        return None


def fetch_leetcode_rating(username: str) -> Optional[float]:
    """
    Fetch LeetCode rating (attempts API, falls back to scraping).
    
    Args:
        username: LeetCode username
        
    Returns:
        Rating as float or None if failed
    """
    if not username or not isinstance(username, str):
        return None
    
    username = username.strip()
    if not username:
        return None
    
    # Try GraphQL API first
    try:
        url = "https://leetcode.com/graphql"
        query = """
        query userPublicProfile($username: String!) {
            matchedUser(username: $username) {
                username
                profile {
                    ranking
                }
                contestBadge {
                    name
                }
            }
        }
        """
        
        payload = {
            "query": query,
            "variables": {"username": username}
        }
        
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0"
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if "data" in data and "matchedUser" in data["data"]:
            matched_user = data["data"]["matchedUser"]
            
            # LeetCode doesn't expose rating directly, but we can estimate from ranking
            # This is a simplified approach - actual rating calculation is complex
            profile = matched_user.get("profile", {})
            ranking = profile.get("ranking")
            
            if ranking is not None:
                # Rough estimation: lower ranking = higher rating
                # This is not accurate but provides a proxy
                # For now, return None as LeetCode rating is not publicly available via API
                logger.info(f"Found LeetCode profile for {username}, but rating not available")
                return None
        
        logger.warning(f"No profile found for LeetCode user: {username}")
        return None
        
    except requests.exceptions.Timeout:
        logger.warning(f"Timeout fetching LeetCode data for {username}")
    except requests.exceptions.RequestException as e:
        logger.warning(f"Error fetching LeetCode data: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error fetching LeetCode data: {str(e)}")
    
    # LeetCode rating is not publicly available via API
    # Would require authenticated access or scraping (which may violate ToS)
    return None


def fetch_ratings(cf_username: Optional[str] = None, lc_username: Optional[str] = None) -> Dict[str, Optional[float]]:
    """
    Fetch ratings for both platforms.
    
    Args:
        cf_username: Codeforces username
        lc_username: LeetCode username
        
    Returns:
        Dictionary with 'cf_rating' and 'lc_rating' keys
    """
    result = {
        "cf_rating": None,
        "lc_rating": None
    }
    
    if cf_username:
        # Rate limiting: wait a bit between requests
        result["cf_rating"] = fetch_codeforces_rating(cf_username)
        time.sleep(0.5)  # Avoid rate limiting
    
    if lc_username:
        result["lc_rating"] = fetch_leetcode_rating(lc_username)
        time.sleep(0.5)
    
    return result
