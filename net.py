import aiohttp
import asyncio
import json
import time

# URLs
BASE_API_URL = "https://amt.x10.mx/get/?r={db_number}"  # URL template with placeholder
CLAIM_URL = "https://apis.mytel.com.mm/daily-quest-v3/api/v3/daily-quest/daily-claim"
TEST_URL = "https://apis.mytel.com.mm/network-test/v3/submit"

# Configuration
OPERATORS = ["MYTEL", "MPT", "OOREDOO", "ATOM"]
DATABASES = [1, 2, 3, 4]  # Add more database numbers as needed
BACKUP_FILE = "backup.json"

async def fetch_json_data(session, db_number):
    """Fetch JSON data from the API for a specific database number."""
    api_url = BASE_API_URL.format(db_number=db_number)
    print(f"Fetching data from database {db_number}...")
    
    try:
        async with session.get(api_url) as response:
            if response.status == 200:
                data = await response.json()
                with open(BACKUP_FILE, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4)
                print(f"Data from database {db_number} fetched successfully")
                return data
            print(f"Failed to fetch database {db_number}. Status: {response.status}")
            return None
    except Exception as e:
        print(f"Error fetching database {db_number}: {str(e)}")
        return None

async def send_claim_request(session, access_token, msisdn):
    """Send a daily claim request."""
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    payload = {"msisdn": msisdn.replace("%2B959", "+959")}

    try:
        async with session.post(CLAIM_URL, json=payload, headers=headers) as response:
            response_text = await response.text()
            status = "Success" if response.status == 200 else "Failed"
            print(f"[Claim] {msisdn}: {status} - {response_text}")
    except Exception as e:
        print(f"[Claim] Error for {msisdn}: {str(e)}")

async def send_network_test_request(session, number, api_key, operator):
    """Send network test request for an operator."""
    payload = {
        "cellId": "51273751",
        "deviceModel": "Redmi Note 8 Pro",
        "downloadSpeed": 0.8,
        "enb": "200288",
        "latency": 734.875,
        "latitude": "21.4631248",
        "location": "Mandalay Region, Myanmar (Burma)",
        "longitude": "95.3621706",
        "msisdn": number.replace("%2B959", "+959"),
        "networkType": "_4G",
        "operator": operator,
        "requestId": number,
        "requestTime": time.strftime("%Y-%m-%d %H:%M:%S"),
        "rsrp": "-98",
        "township": "Mandalay Region",
        "uploadSpeed": 10.0
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    try:
        async with session.post(TEST_URL, json=payload, headers=headers) as response:
            response_text = await response.text()
            status = "Success" if response.status == 200 else "Failed"
            print(f"[Test] {number} - {operator}: {status} - {response_text}")
    except Exception as e:
        print(f"[Test] Error for {number} - {operator}: {str(e)}")

async def process_database(db_number):
    """Process all requests for a single database."""
    async with aiohttp.ClientSession() as session:
        # Fetch data for current database
        data = await fetch_json_data(session, db_number)
        if not data:
            return

        # Wait for user confirmation
       

    # Process requests
    async with aiohttp.ClientSession() as session:
        # Create tasks
        claim_tasks = [
            send_claim_request(session, item["access"], item["phone"])
            for item in data
        ]
        
        network_tasks = [
            send_network_test_request(session, item["phone"], item["access"], operator)
            for item in data
            for operator in OPERATORS
        ]

        # Execute all tasks
        await asyncio.gather(*claim_tasks, *network_tasks)
        print(f"\nDatabase {db_number} processing completed\n")

async def main():
    """Main function to process all databases sequentially."""
    for db_number in DATABASES:
        await process_database(db_number)

if __name__ == "__main__":
    print("Starting script execution...")
    asyncio.run(main())
    print("All databases processed successfully")
