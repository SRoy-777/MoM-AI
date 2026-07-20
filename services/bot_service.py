import logging
import asyncio
from typing import Dict, Any, Optional

logger = logging.getLogger("mom_ai.bot")

class TeamsBotService:
    def __init__(self):
        self.active_sessions = {}

    def join_teams_meeting(self, meeting_url: str, bot_name: str = "MoM AI Note Taker") -> Dict[str, Any]:
        """
        Launches Playwright headless Chromium to join MS Teams web link as Guest.
        Note: MS Teams meetings may hold guest bots in the Lobby until the meeting host admits them.
        """
        logger.info(f"Initiating Playwright Teams Guest Join: {meeting_url} as '{bot_name}'")
        session_id = f"session_{len(self.active_sessions) + 1}"

        # Trigger async Playwright task in background
        try:
            loop = asyncio.get_event_loop()
            loop.create_task(self._run_playwright_bot(session_id, meeting_url, bot_name))
        except Exception as e:
            logger.error(f"Failed to launch Playwright task: {e}")

        self.active_sessions[session_id] = {
            "url": meeting_url,
            "bot_name": bot_name,
            "status": "joining"
        }

        return {
            "success": True,
            "session_id": session_id,
            "message": f"Bot '{bot_name}' is launching Chromium to join Teams. Check your Teams Lobby to admit the bot!"
        }

    async def _run_playwright_bot(self, session_id: str, meeting_url: str, bot_name: str):
        try:
            from playwright.async_api import async_playwright
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        "--use-fake-ui-for-media-stream",
                        "--use-fake-device-for-media-stream",
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-blink-features=AutomationControlled"
                    ]
                )
                context = await browser.new_context(
                    permissions=["microphone", "camera"],
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
                page = await context.new_page()

                logger.info(f"[{session_id}] Navigating to Teams meeting URL...")
                await page.goto(meeting_url)
                await page.wait_for_timeout(3000)

                # Try clicking 'Continue on this browser' if prompted
                try:
                    continue_btn = page.locator("button:has-text('Continue on this browser')")
                    if await continue_btn.is_visible(timeout=5000):
                        await continue_btn.click()
                except Exception:
                    pass

                await page.wait_for_timeout(5000)

                # Type Guest Name if input field is present
                try:
                    name_input = page.locator("input[placeholder*='name'], input[aria-label*='name']")
                    if await name_input.is_visible(timeout=5000):
                        await name_input.fill(bot_name)
                except Exception:
                    pass

                # Click 'Join now' button
                try:
                    join_btn = page.locator("button:has-text('Join now'), button:has-text('Join')")
                    if await join_btn.is_visible(timeout=5000):
                        await join_btn.click()
                        logger.info(f"[{session_id}] Clicked 'Join now'. Bot is in meeting or lobby.")
                except Exception:
                    pass

                self.active_sessions[session_id]["status"] = "in_lobby"

                # Keep page open during active session
                while session_id in self.active_sessions:
                    await asyncio.sleep(2)

                await browser.close()
        except Exception as e:
            logger.error(f"[{session_id}] Playwright bot error: {e}")
            if session_id in self.active_sessions:
                self.active_sessions[session_id]["status"] = "error"

    def leave_teams_meeting(self, session_id: str) -> Dict[str, Any]:
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
            return {"success": True, "message": "Bot left the meeting."}
        return {"success": False, "error": "Session not found."}
