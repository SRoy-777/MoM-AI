import os
import json
import logging
from typing import Dict, Any, List, Optional
from google import genai
from google.genai import types

logger = logging.getLogger("mom_ai.gemini")

class GeminiMoMService:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if self.api_key:
            self.client = genai.Client(api_key=self.api_key)
        else:
            self.client = None

    def update_api_key(self, api_key: str):
        self.api_key = api_key
        self.client = genai.Client(api_key=api_key)

    def generate_mom(
        self,
        transcript: str,
        human_notes: str = "",
        manual_tasks: List[Dict[str, Any]] = None,
        meeting_title: str = "Meeting Minutes",
        meeting_date: str = "",
        attendees: str = ""
    ) -> Dict[str, Any]:
        """
        Generates structured Minutes of Meeting (MoM) using Gemini 2.0 Flash (1M+ token window).
        Fuses full meeting transcript with Human Assistant live notes & manual task assignments.
        """
        if not self.client:
            raise ValueError("GEMINI_API_KEY is not configured. Please provide your Google Gemini API key.")

        manual_tasks = manual_tasks or []

        prompt = f"""
You are an Executive AI Secretary and Minutes of Meeting (MoM) Specialist.
Analyze the following meeting transcript (which may be up to 4 hours long) and the Human Assistant's live co-pilot notes.
Generate a comprehensive, high-standard, structured Minutes of Meeting report in valid JSON format.

=== MEETING DETAILS ===
Title: {meeting_title}
Date: {meeting_date}
Attendees: {attendees}

=== HUMAN ASSISTANT LIVE NOTES ===
{human_notes if human_notes.strip() else "None provided."}

=== HUMAN ASSISTANT MANUAL TASK MATRIX ===
{json.dumps(manual_tasks, indent=2) if manual_tasks else "None provided."}

=== FULL MEETING TRANSCRIPT ===
{transcript if transcript.strip() else "No audio transcript available. Rely on Human Notes."}

=== INSTRUCTIONS & REQUIREMENTS ===
1. Executive Summary: Provide a 3-4 sentence high-level executive summary of what was discussed and accomplished.
2. Agenda & Discussion Highlights: Group key discussions into logical topics/chapters with clear bullet points.
3. Key Decisions Made: Highlight binding decisions, policy updates, or approvals made during the meeting.
4. Action Items & Task Matrix:
   - Extract ALL action items from both the transcript and the Human Assistant's manual tasks.
   - For every task, identify:
     - `task`: Clear description of the deliverable.
     - `assignee`: Person responsible (or "Unassigned").
     - `department`: Department responsible (e.g., Engineering, Marketing, Finance, Sales, HR, Management, Ops).
     - `timeframe`: Target delivery timeframe or due date (e.g., EOD Friday, Q3 W2, July 28th, ASAP).
     - `priority`: High, Medium, or Low.
     - `status`: Pending.
5. Risks & Open Questions: Any unresolved issues, pending follow-ups, or potential risks identified.

Respond STRICTLY with a JSON object matching this schema:
{{
  "title": "{meeting_title}",
  "date": "{meeting_date}",
  "attendees": "{attendees}",
  "executive_summary": "string",
  "discussion_highlights": [
    {{
      "topic": "string",
      "points": ["string"]
    }}
  ],
  "decisions": ["string"],
  "action_items": [
    {{
      "task": "string",
      "assignee": "string",
      "department": "string",
      "timeframe": "string",
      "priority": "High | Medium | Low",
      "status": "Pending"
    }}
  ],
  "risks_and_open_questions": ["string"],
  "human_notes_summary": "string"
}}
"""

        try:
            response = self.client.models.generate_content(
                model='gemini-2.0-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.2,
                ),
            )

            text_output = response.text
            parsed_mom = json.loads(text_output)
            return parsed_mom

        except Exception as e:
            logger.error(f"Error calling Gemini API: {e}")
            raise e
