import asyncio
import os
import sys
from dotenv import load_dotenv

# Load env before importing app modules
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from app.services.amazon_client import SPAPIAmazonClient

async def test_amazon_connection():
    print("Initializing Amazon SP-API Client...")
    try:
        client = SPAPIAmazonClient()
        print("Client initialized. Attempting to fetch marketplace participations...")
        
        # Calling sellers API to get marketplace participations (a lightweight endpoint)
        endpoint = f"{client.endpoint}/sellers/v1/marketplaceParticipations"
        response = await client._request("GET", endpoint)
        
        print("\n✅ SUCCESS! Connection to Amazon SP-API is working perfectly.")
        print(f"Marketplaces Authorized: {len(response.get('payload', []))}")
        for mp in response.get('payload', []):
            print(f" - {mp['marketplace']['name']} ({mp['marketplace']['countryCode']})")
            
    except Exception as e:
        print("\n❌ FAILURE! Could not connect to Amazon SP-API.")
        print(f"Error Details: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_amazon_connection())
