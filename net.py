import requests
import json
import time
import random
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def make_request(method, url, headers=None, data=None, retries=3):
    """Send HTTP request with retries and logging"""
    for attempt in range(retries):
        try:
            response = requests.request(
                method, url, headers=headers, json=data, timeout=(3.05, 27)
            )
            status_code = response.status_code

            if 200 <= status_code < 300:
                logger.info(f"✅ [{method}] {url} -> {status_code}")
                try:
                    return response.json()
                except json.JSONDecodeError:
                    logger.warning(f"⚠️ [{method}] Invalid JSON response from {url}")
                    return response.text  # Return raw text if JSON parsing fails

            elif status_code >= 500:
                logger.warning(f"⚠️ [{method}] Server error {status_code} for {url}")
            
            else:
                logger.warning(f"❌ [{method}] Request failed {status_code} for {url}")

        except requests.RequestException as e:
            logger.error(f"🚨 [{method}] Error: {e}")

        if attempt < retries - 1:
            sleep_time = 2 ** attempt + random.uniform(0, 1)
            logger.info(f"🔄 Retrying in {sleep_time:.2f}s...")
            time.sleep(sleep_time)

    logger.error(f"⛔ Max retries exceeded for {url}")
    return None

def process_user(user):
    """Process a user's claim actions with structured logging"""
    required_fields = {'username', 'phone', 'userid', 'access'}
    if not required_fields.issubset(user.keys()):
        logger.error(f"🚫 Invalid user data: {user}")
        return

    username = user['username']
    phone = user['phone']
    userid = user['userid']
    access = user['access']

    logger.info(f"\n📌 Processing User: {username} ({phone})")

    base_headers = {
        "Authorization": f"Bearer {access}",
        "User-Agent": "MyTM/4.11.0/Android/30",
        "X-Server-Select": "production",
        "Device-Name": "Xiaomi Redmi Note 8 Pro",
        "Host": "store.atom.com.mm"
    }

    # Step 1: Dashboard request
    dashboard_url = (
        f"https://store.atom.com.mm/my/dashboard?isFirstTime=1&isFirstInstall=0"
        f"&msisdn={phone}&userid={userid}&v=4.11.0"
    )
    make_request('GET', dashboard_url, headers=base_headers)

    # Step 2: Fetch claim list
    claim_url = (
        f"https://store.atom.com.mm/mytmapi/v1/my/point-system/claim-list"
        f"?msisdn={phone}&userid={userid}&v=4.11.0"
    )
    claim_data = make_request('GET', claim_url, headers=base_headers)
    
    if not isinstance(claim_data, dict) or 'data' not in claim_data or 'attribute' not in claim_data['data']:
        logger.error(f"⚠️ No valid claims for {username}")
        return

    claims = [c for c in claim_data['data']['attribute'] if c.get('enable') is True]
    
    logger.info(f"🔎 {len(claims)} claim(s) found for {username}")

    # Step 3: Process claims
    for claim in claims:
        if 'id' not in claim or 'campaign_name' not in claim:
            logger.warning(f"⚠️ Skipping invalid claim: {claim}")
            continue
            
        claim_id = claim['id']
        campaign_name = claim['campaign_name']
        logger.info(f"💰 Claiming '{campaign_name}' (ID: {claim_id})")

        post_url = (
            f"https://store.atom.com.mm/mytmapi/v1/my/point-system/claim"
            f"?msisdn={phone}&userid={userid}&v=4.11.0"
        )
        response = make_request('POST', post_url, headers=base_headers, data={'id': claim_id})

        if response and isinstance(response, dict):
            message = response.get('data', {}).get('attribute', {}).get('message', 'Unknown')
            logger.info(f"✅ {campaign_name}: {message}")
        else:
            logger.warning(f"❌ Claim failed for '{campaign_name}'")

    # Step 4: Refresh user data
    refresh_url = f"https://api.xalyon.xyz/v2/refresh/?phone={phone}"
    make_request('GET', refresh_url)

    logger.info(f"🔄 Refresh completed for {username}")

    # Small delay to prevent CPU overload
    time.sleep(0.5)

def main():
    """Main execution with controlled concurrency"""
    user_data_url = "https://api.xalyon.xyz/v2/atom/index.php?endpoint=admin_view"
    
    users = make_request('GET', user_data_url)
    if not isinstance(users, list):
        logger.error("⛔ Failed to retrieve users")
        return

    max_workers = min(4, len(users))  # Limit concurrency to 4
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        executor.map(process_user, users)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("⛔ Process interrupted by user")
    except Exception as e:
        logger.error(f"🚨 Critical error: {e}")
