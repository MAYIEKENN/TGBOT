import aiohttp
import asyncio
import json
import time

# URLs
API_URL = "https://amt.x10.mx/index.php?endpoint=admin_view"  # Replace with your actual JSON API URL
CLAIM_URL = "https://apis.mytel.com.mm/daily-quest-v3/api/v3/daily-quest/daily-claim"
TEST_URL = "https://apis.mytel.com.mm/network-test/v3/submit"

# Operators List
OPERATORS = ["MYTEL", "MPT", "OOREDOO", "ATOM"]

# Backup file
BACKUP_FILE = "/storage/emulated/0/MySrc/mytel/backup.json"

async def fetch_json_data(session):
    """Fetch JSON data from the API and save to backup.json."""
    print("Fetching JSON data from API...")
    try:
        async with session.get(API_URL) as response:
            if response.status == 200:
                data = await response.json()
                with open(BACKUP_FILE, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4)
                print("JSON data fetched and saved to backup.json.")
                return data
            else:
                print(f"Failed to fetch JSON data. HTTP Code: {response.status}")
                return None
    except Exception as e:
        print(f"Error fetching JSON data: {str(e)}")
        return None

async def send_claim_request(session, access_token, msisdn):
    """Send a request to claim daily rewards."""
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    payload = {"msisdn": msisdn.replace("%2B959", "+959")}

    try:
        async with session.post(CLAIM_URL, json=payload, headers=headers) as response:
            response_text = await response.text()
            status = "Success" if response.status == 200 else "Failed"
            print(f"[Daily Claim] {msisdn}: {status} - Response: {response_text}")
    except Exception as e:
        print(f"[Daily Claim] Error for {msisdn}: {str(e)}")

async def send_network_test_request(session, number, api_key, operator):
    """Send a network test request for each operator."""
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
            print(f"[Network Test] {number} - {operator}: {status} - Response: {response_text}")
    except Exception as e:
        print(f"[Network Test] Error for {number} - {operator}: {str(e)}")

async def main():
    """Main function to handle API requests asynchronously."""
    async with aiohttp.ClientSession() as session:
        json_data = await fetch_json_data(session)
        if not json_data:
            print("No data to process. Exiting...")
            return

    input("\nPress Enter to start processing requests...\n")

    async with aiohttp.ClientSession() as session:
        # Tasks for daily claim requests
        claim_tasks = [send_claim_request(session, item["access"], item["phone"]) for item in json_data]

        # Tasks for network test requests
        network_tasks = [
            send_network_test_request(session, item["phone"], item["access"], operator)
            for item in json_data for operator in OPERATORS
        ]

        # Run all tasks asynchronously
        await asyncio.gather(*claim_tasks, *network_tasks)
        print("\nAll requests completed.")

if __name__ == "__main__":
    try:
        loop = asyncio.get_running_loop()
        loop.run_until_complete(main())
    except RuntimeError:
        asyncio.run(main())

    print("Script execution completed.")
