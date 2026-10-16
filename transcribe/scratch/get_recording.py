import asyncio
import sys
sys.path.insert(0, ".")
from app.providers.fireflies import FirefliesProvider

async def main():
    p = FirefliesProvider()
    query = """
    query {
      transcripts(limit: 5) {
        id
        title
        transcript_url
        duration
        date
        sentences {
          speaker_name
          text
          start_time
          end_time
        }
      }
    }
    """
    res = await p._execute_graphql(query)
    transcripts = res.get("transcripts", [])
    for t in transcripts:
        print("="*60)
        print("Transcript ID:", t.get("id"))
        print("Title:", t.get("title"))
        print("Transcript URL:", t.get("transcript_url"))
        print("Duration (s):", t.get("duration"))
        print("Sentences:")
        for s in t.get("sentences", []):
            print(f"  [{s.get('start_time')}s - {s.get('end_time')}s] {s.get('speaker_name')}: {s.get('text')}")

if __name__ == "__main__":
    asyncio.run(main())
