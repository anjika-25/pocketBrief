---
description: Automatically include timestamps when summarizing tutorial or lecture videos
---
To have the AI automatically include timestamps when generating summaries, you need to update the prompt it uses for generating the summary. Follow these steps:

1. Open `c:\Users\Aakif Khan\ytsummary\youtube_rag_assistant\modules\groq_llm.py`.
2. Locate the `TUTORIAL_SUMMARIZE_PROMPT` variable definition.
3. Add a clear instruction to the "Your Task" section to extract and include timestamps from the provided transcript.
4. Modify the "Format" section to instruct the AI to format the breakdown with timestamps.

Example modification:

```diff
 TUTORIAL_SUMMARIZE_PROMPT = """You are LectureAI — an expert technical tutor.
 
 Your Task:
-Summarize this tutorial/lecture video transcript. Focus on the "how-to" aspects, key concepts, and any code or steps mentioned.
+Summarize this tutorial/lecture video transcript. Focus on the "how-to" aspects, key concepts, and any code or steps mentioned. The provided transcript includes detailed timestamps for every line. You MUST extract these timestamps and include the relevant starting timestamp for each step or major topic in your summary, so the user can easily find that part of the video.
 
 Format:
 1.  **Overview**: What is being taught?
-2.  **Step-by-Step Breakdown**: The main phases or steps of the tutorial.
+2.  **Step-by-Step Breakdown**: The main phases or steps of the tutorial. Format each step starting with its corresponding timestamp (e.g., [12:34] - Set up the database...).
 3.  **Key Concepts**: Important definitions or theories explained.
 4.  **Summary Note**: A final concise takeaway.
```
