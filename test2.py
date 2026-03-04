import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from app import process_video, VideoRequest
import logging

logging.basicConfig(level=logging.INFO)

async def main():
    req = VideoRequest(url="https://www.youtube.com/watch?v=jNQXAC9IVRw", video_id="test_vid_2")
    try:
        res = await process_video(req)
        print("Success:", res)
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
