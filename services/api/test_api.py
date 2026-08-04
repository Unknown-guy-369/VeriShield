import asyncio
import httpx
from asgi_lifespan import LifespanManager
from app.main import app

async def test_api():
    async with LifespanManager(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            # 1. Create analysis
            response = await client.post(
                "/analyses",
                json={"input": "The earth is flat."},
                headers={"Content-Type": "application/json"}
            )
            print("Create response:", response.status_code)
            if response.status_code != 201:
                print(response.text)
                return
                
            data = response.json()
            analysis_id = data["id"]
            print("Analysis ID:", analysis_id)
            print("Status:", data["status"])
            
            # 2. Poll for completion
            for _ in range(10):
                await asyncio.sleep(1)
                resp = await client.get(f"/analyses/{analysis_id}")
                data = resp.json()
                print(f"Polled status: {data['status']} - Progress: {data['progress']}")
                if data["status"] in ("COMPLETED", "FAILED"):
                    print("Final result found!")
                    break

if __name__ == "__main__":
    asyncio.run(test_api())
