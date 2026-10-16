from google import genai
from google.genai import types
from app.core.config import get_settings
import json
import logging

logger = logging.getLogger(__name__)

VERIFICATION_PROMPT = """
You are a code review assistant for a task management system.

Your job is to analyze a Git commit diff and determine whether it implements a specific task.

## Task Details
- **Title:** {title}
- **Description:** {description}
- **Keywords to look for:** {keywords}

## Commit Information
- **Commit SHA:** {commit_sha}
- **Commit Message:** {commit_message}
- **Author:** {author}

## Git Diff
```diff
{diff}
```

## Instructions
Analyze the diff carefully and respond with ONLY a valid JSON object in this exact format:
{{
  "confidence_score": <number between 0 and 100>,
  "implements_task": <true or false>,
  "reasoning": "<brief explanation of your assessment>",
  "matched_keywords": ["<keyword1>", "<keyword2>"]
}}

Scoring guidelines:
- 90-100: Clear, complete implementation of the task with all keywords present
- 70-89: Partial implementation, most of the task is done
- 50-69: Related changes but task not fully implemented
- 0-49: Unrelated to the task
"""


class GeminiService:
    def __init__(self):
        settings = get_settings()
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model = settings.gemini_model

    async def verify_commit(
        self,
        task_title: str,
        task_description: str,
        task_keywords: list[str],
        commit_sha: str,
        commit_message: str,
        author: str,
        diff: str,
    ) -> dict:
        """
        Send the commit diff + task context to Gemini Flash and parse the verification result.
        Returns: { confidence_score, implements_task, reasoning, matched_keywords }
        """
        prompt = VERIFICATION_PROMPT.format(
            title=task_title,
            description=task_description,
            keywords=", ".join(task_keywords),
            commit_sha=commit_sha,
            commit_message=commit_message,
            author=author,
            diff=diff[:12000],  # trim to avoid hitting token limits
        )

        models_to_try = [
            self.model,
            "gemini-flash-lite-latest",
            "gemini-3.5-flash-lite",
            "gemini-3.5-flash",
            "gemini-3.6-flash",
        ]
        # Remove duplicates while preserving order
        models_to_try = list(dict.fromkeys([m for m in models_to_try if m]))

        last_error = None
        for model_name in models_to_try:
            try:
                response = self.client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.1,
                        response_mime_type="application/json",
                    ),
                )
                result = json.loads(response.text)
                logger.info(
                    f"Gemini verification for commit {commit_sha} using {model_name}: "
                    f"score={result.get('confidence_score')}"
                )
                return result
            except Exception as e:
                last_error = e
                logger.warning(f"Gemini verification attempt failed with {model_name}: {e}")

        logger.error(f"Gemini verification failed for commit {commit_sha}: {last_error}")
        return {
            "confidence_score": 0,
            "implements_task": False,
            "reasoning": f"Verification failed: {str(last_error)}",
            "matched_keywords": [],
        }
