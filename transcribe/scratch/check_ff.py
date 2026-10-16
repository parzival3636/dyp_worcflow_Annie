import asyncio
import sys
sys.path.insert(0, ".")
from app.providers.fireflies import FirefliesProvider

async def main():
    p = FirefliesProvider()
    query = """
    query {
      transcripts {
        id
        title
        date
        duration
        is_live
        meeting_link
      }
    }
    """
    res = await p._execute_graphql(query)
    transcripts = res.get("transcripts", [])
    print("Found transcripts:", len(transcripts))
    for t in transcripts:
        print("Transcript:", t)

if __name__ == "__main__":
    asyncio.run(main())
