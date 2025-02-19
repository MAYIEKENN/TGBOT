import requests
import json
import time
import random
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def get_modified_since():
    """Generate If-Modified-Since header value with UTC time"""
    try:
        yesterday = datetime.utcnow() - timedelta(days=1)
        return yesterday.strftime("%a, %d %b %Y %H:%M:%S GMT")
    except Exception as e:
        logger.error(f"Date calculation error: {e}")
        return datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")

def make_request(method, url, headers=None, data=None, retries=3):
    """Generic request handler with exponential backoff"""
    for attempt in range(retries):
        try:
            response = requests.request(
                method,
                url,
                headers=headers,
                json=data,
                timeout=(3.05, 27)
            )

            logger.info(f"{method} {url} -> {response.status_code}")

            if 200 <= response.status_code < 300:
                try:
                    return response.json()
                except json.JSONDecodeError:
                    logger.error("Invalid JSON response, returning raw text")
                    return response.text  # Return raw response text if JSON parsing fails

            logger.warning(f"Request failed: {response.status_code}")
            if response.status_code >= 500:
                logger.debug(f"Server error response: {response.text}")

        except requests.RequestException as e:
            logger.error(f"Request error: {e}")

        if attempt < retries - 1:
            sleep_time = 2 ** attempt + random.uniform(0, 1)
            logger.info(f"Retrying in {sleep_time:.2f}s...")
            time.sleep(sleep_time)

    logger.error(f"Max retries exceeded for {url}")
    return None

def process_user(user):
    """Process user claims with enhanced validation, then refresh user data"""
    required_fields = {'username', 'phone', 'userid', 'access'}
    if not required_fields.issubset(user.keys()):
        logger.error(f"Invalid user data: {user}")
        return

    user_info = {k: user[k] for k in required_fields}
    logger.info(f"Processing User: {user_info['username']} ({user_info['phone']})")

    # Prepare headers with all required fields
    base_headers = {
        "Authorization": f"Bearer {user_info['access']}",
        "User-Agent": "MyTM/4.11.0/Android/30",
        "X-Server-Select": "production",
        "Device-Name": "Xiaomi Redmi Note 8 Pro",
        "Host": "store.atom.com.mm"
    }

    # First request: dashboard endpoint (with same headers)
    dashboard_url = (
        f"https://store.atom.com.mm/my/dashboard?isFirstTime=1&isFirstInstall=0"
        f"&msisdn={user_info['phone']}"
        f"&userid={user_info['userid']}"
        f"&v=4.11.0"
    )
    dashboard_response = make_request('GET', dashboard_url, headers=base_headers)
    logger.info(f"Dashboard response for {user_info['username']}: {dashboard_response}")

    # Fetch claim list
    claim_url = (
        f"https://store.atom.com.mm/mytmapi/v1/my/point-system/claim-list"
        f"?msisdn={user_info['phone']}"
        f"&userid={user_info['userid']}"
        f"&v=4.11.0"
    )
    claim_data = make_request('GET', claim_url, headers=base_headers)
    
    # Validate response structure
    if not isinstance(claim_data, dict) or 'data' not in claim_data or 'attribute' not in claim_data['data']:
        logger.error(f"Invalid claim data format for user {user_info['username']}")
        return

    attributes = claim_data['data']['attribute']
    if not isinstance(attributes, list):
        logger.error(f"Invalid attributes format for user {user_info['username']}")
        return

    # Process enabled claims
    enabled_claims = [attr for attr in attributes if isinstance(attr, dict) and attr.get('enable') is True]
    logger.info(f"Found {len(enabled_claims)} claim(s) for {user_info['username']}")

    for claim in enabled_claims:
        if 'id' not in claim or 'campaign_name' not in claim:
            logger.warning(f"Skipping claim with missing ID or name: {claim}")
            continue
            
        claim_id = claim['id']
        logger.info(f"Claiming {claim['campaign_name']} (ID: {claim_id})")

        # POST request for claiming
        post_url = (
            f"https://store.atom.com.mm/mytmapi/v1/my/point-system/claim"
            f"?msisdn={user_info['phone']}"
            f"&userid={user_info['userid']}"
            f"&v=4.11.0"
        )
        response = make_request('POST', post_url, headers=base_headers, data={'id': claim_id})
        
        if response and isinstance(response, dict):
            message = response.get('data', {}).get('attribute', {}).get('message', 'Unknown response')
            logger.info(f"Claim result for {claim['campaign_name']}: {message}")
        else:
            logger.warning(f"Claim attempt failed for {claim['campaign_name']}")

    # After processing claims, call the refresh endpoint without any headers
    refresh_url = f"https://api.xalyon.xyz/v2/refresh/?phone={user_info['phone']}"
    refresh_response = make_request('GET', refresh_url)
    logger.info(f"Refresh response for {user_info['username']}: {refresh_response}")

    # Brief pause to help manage load
    time.sleep(0.5)

def main():
    """Main execution flow"""
    user_data_url = "https://api.xalyon.xyz/v2/atom/index.php?endpoint=admin_view"
    
    # Fetch user data with retries
    users = make_request('GET', user_data_url)
    
    if not isinstance(users, list):
        logger.error("Invalid user data format")
        return

    # For a 4‑core VPS with 4GB RAM, limit concurrency to 4 threads.
    max_workers = min(4, len(users))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        executor.map(process_user, users)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
    except Exception as e:
        logger.error(f"Critical error: {e}")
