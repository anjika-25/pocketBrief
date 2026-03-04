"""
YouTube Video Search — uses yt-dlp's search to find real, available videos.
Returns actual working YouTube links for any query.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def search_youtube(query: str, max_results: int = 5) -> list[dict]:
    """
    Search YouTube for videos matching the query using yt-dlp.
    Returns real, verified video results that are actually available.

    Args:
        query: Search query string.
        max_results: Maximum number of results to return (1-10).

    Returns:
        List of dicts with keys: title, url, video_id, duration, channel, view_count
    """
    import yt_dlp

    max_results = min(max(max_results, 1), 10)
    search_url = f"ytsearch{max_results}:{query}"

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": False,  # Full extraction to verify availability
        "skip_download": True,
        "ignoreerrors": True,
        "no_color": True,
    }

    results = []

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(search_url, download=False)

            if not info or "entries" not in info:
                logger.warning("No search results found for: %s", query)
                return []

            for entry in info["entries"]:
                if entry is None:
                    continue  # skipped due to error (unavailable)

                video_id = entry.get("id", "")
                title = entry.get("title", "Unknown")
                duration = entry.get("duration")
                channel = entry.get("channel") or entry.get("uploader", "Unknown")
                view_count = entry.get("view_count")
                upload_date = entry.get("upload_date", "")

                # Format duration as MM:SS or HH:MM:SS
                duration_str = ""
                if duration:
                    mins, secs = divmod(int(duration), 60)
                    hours, mins = divmod(mins, 60)
                    if hours:
                        duration_str = f"{hours}:{mins:02d}:{secs:02d}"
                    else:
                        duration_str = f"{mins}:{secs:02d}"

                # Format view count
                view_str = ""
                if view_count:
                    if view_count >= 1_000_000:
                        view_str = f"{view_count / 1_000_000:.1f}M views"
                    elif view_count >= 1_000:
                        view_str = f"{view_count / 1_000:.1f}K views"
                    else:
                        view_str = f"{view_count} views"

                # Format upload date
                date_str = ""
                if upload_date and len(upload_date) == 8:
                    date_str = f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:8]}"

                results.append({
                    "title": title,
                    "url": f"https://www.youtube.com/watch?v={video_id}",
                    "video_id": video_id,
                    "duration": duration_str,
                    "channel": channel,
                    "views": view_str,
                    "upload_date": date_str,
                })

        logger.info("Found %d results for query: %s", len(results), query)

    except Exception as e:
        logger.error("YouTube search failed: %s", e)

    return results


def format_search_results_for_llm(results: list[dict]) -> str:
    """
    Format search results into a text block the LLM can include in its answer.
    Designed to be human-readable and NOT contain raw URLs (for TTS).
    """
    if not results:
        return "No videos found for this search."

    lines = []
    for i, r in enumerate(results, 1):
        parts = [f"{i}. **{r['title']}**"]
        if r.get("channel"):
            parts.append(f"   by {r['channel']}")
        meta = []
        if r.get("duration"):
            meta.append(r["duration"])
        if r.get("views"):
            meta.append(r["views"])
        if r.get("upload_date"):
            meta.append(f"uploaded {r['upload_date']}")
        if meta:
            parts.append(f"   ({', '.join(meta)})")
        lines.append("\n".join(parts))

    return "\n\n".join(lines)


def format_search_results_for_display(results: list[dict]) -> str:
    """
    Format search results with clickable links for the chat UI (not TTS).
    """
    if not results:
        return "No videos found for this search."

    lines = []
    for i, r in enumerate(results, 1):
        parts = [f"**{i}. [{r['title']}]({r['url']})**"]
        meta = []
        if r.get("channel"):
            meta.append(f"by {r['channel']}")
        if r.get("duration"):
            meta.append(r["duration"])
        if r.get("views"):
            meta.append(r["views"])
        if r.get("upload_date"):
            meta.append(f"uploaded {r['upload_date']}")
        if meta:
            parts.append(f"   {' · '.join(meta)}")
        lines.append("\n".join(parts))

    return "\n\n".join(lines)


if __name__ == "__main__":
    results = search_youtube("python tutorial for beginners 2024", max_results=3)
    print(format_search_results_for_display(results))
