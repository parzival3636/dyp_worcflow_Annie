import asyncio
import sys
sys.path.insert(0, ".")
from app.providers.fireflies import FirefliesProvider, ADD_BOT_MUTATION

async def main():
    p = FirefliesProvider()
    data = await p._execute_graphql(ADD_BOT_MUTATION, variables={"link": "https://meet.google.com/sma-nocn-amd"})
    print("addToLiveMeeting response:", data)

if __name__ == "__main__":
    asyncio.run(main())
