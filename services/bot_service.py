import logging
import asyncio
from typing import Dict, Any, Optional

logger = logging.getLogger("mom_ai.bot")

class TeamsBotService:
    def __init__(self):
        self.active_sessions = {}

    def get_status(self, session_id: str = "") -> Dict[str, Any]:
        if session_id and session_id in self.active_sessions:
            return {"success": True, "session": self.active_sessions[session_id]}
        return {"success": True, "sessions": self.active_sessions}

    def join_teams_meeting(self, meeting_url: str, bot_name: str = "MoM AI Note Taker") -> Dict[str, Any]:
        """
        Launches Playwright headless Chromium to join MS Teams web link as Guest.
        """
        logger.info(f"Initiating Playwright Teams Guest Join: {meeting_url} as '{bot_name}'")
        session_id = f"session_{len(self.active_sessions) + 1}"

        self.active_sessions[session_id] = {
            "url": meeting_url,
            "bot_name": bot_name,
            "status": "launching_browser",
            "log": ["Initiating Playwright Chromium..."]
        }

        try:
            loop = asyncio.get_event_loop()
            loop.create_task(self._run_playwright_bot(session_id, meeting_url, bot_name))
        except Exception as e:
            logger.error(f"Failed to launch Playwright task: {e}")
            self.active_sessions[session_id]["status"] = "error"
            self.active_sessions[session_id]["log"].append(f"Launch error: {str(e)}")

        return {
            "success": True,
            "session_id": session_id,
            "message": f"Bot '{bot_name}' is launching Chromium to join Teams meeting. Check status for updates."
        }

    async def _run_playwright_bot(self, session_id: str, meeting_url: str, bot_name: str):
        session_data = self.active_sessions.get(session_id)
        if not session_data:
            return

        def add_log(msg: str):
            logger.info(f"[{session_id}] {msg}")
            session_data["log"].append(msg)

        try:
            from playwright.async_api import async_playwright
            async with async_playwright() as p:
                add_log("Launching Chromium headless browser...")
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        "--use-fake-ui-for-media-stream",
                        "--use-fake-device-for-media-stream",
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-blink-features=AutomationControlled"
                    ]
                )
                context = await browser.new_context(
                    permissions=["microphone", "camera"],
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                    viewport={"width": 1280, "height": 720}
                )
                page = await context.new_page()

                add_log(f"Navigating to Teams URL: {meeting_url[:60]}...")
                session_data["status"] = "navigating"
                await page.goto(meeting_url, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(4000)

                # 1. Click "Continue on this browser" / "Use Teams on the web"
                add_log("Checking for 'Continue on this browser' button...")
                continue_selectors = [
                    "button#openTeamsInApp",
                    "a[data-tid='joinOnWeb']",
                    "button[data-tid='joinOnWeb']",
                    "button:has-text('Continue on this browser')",
                    "a:has-text('Continue on this browser')",
                    "button:has-text('Use Teams on the web')",
                    "a:has-text('Use Teams on the web')"
                ]

                clicked_continue = False
                for sel in continue_selectors:
                    try:
                        btn = page.locator(sel).first
                        if await btn.is_visible(timeout=2000):
                            await btn.click()
                            add_log(f"Clicked 'Continue on browser' using selector: {sel}")
                            clicked_continue = True
                            break
                    except Exception:
                        continue

                if not clicked_continue:
                    add_log("No 'Continue on browser' button needed or found. Proceeding...")

                await page.wait_for_timeout(6000)

                # 2. Enter Guest Name
                add_log("Searching for Guest Name input field...")
                session_data["status"] = "entering_name"

                name_selectors = [
                    "input#username",
                    "input[aria-label*='Enter name']",
                    "input[aria-label*='name']",
                    "input[placeholder*='Type your name']",
                    "input[placeholder*='name']",
                    "input[data-tid='prejoin-display-name-input']",
                    "input[type='text']"
                ]

                filled_name = False
                for sel in name_selectors:
                    try:
                        inp = page.locator(sel).first
                        if await inp.is_visible(timeout=3000):
                            await inp.fill(bot_name)
                            add_log(f"Filled Guest Name '{bot_name}' using selector: {sel}")
                            filled_name = True
                            break
                    except Exception:
                        continue

                if not filled_name:
                    add_log("Warning: Name input field not found directly. Checking page text...")

                await page.wait_for_timeout(2000)

                # 3. Click 'Join Now'
                add_log("Searching for 'Join Now' button...")
                session_data["status"] = "joining_call"

                join_selectors = [
                    "button#join-now",
                    "button[data-tid='prejoin-join-button']",
                    "button:has-text('Join now')",
                    "button:has-text('Join')"
                ]

                joined = False
                for sel in join_selectors:
                    try:
                        btn = page.locator(sel).first
                        if await btn.is_visible(timeout=3000):
                            await btn.click()
                            add_log(f"Clicked 'Join now' using selector: {sel}")
                            joined = True
                            break
                    except Exception:
                        continue

                if joined:
                    session_data["status"] = "waiting_in_lobby_or_joined"
                    add_log("Bot initiated join! Standing by in call / lobby...")
                else:
                    session_data["status"] = "waiting"
                    add_log("Could not find explicit 'Join now' button. Page loaded.")

                # Keep session alive
                while session_id in self.active_sessions:
                    await asyncio.sleep(2)

                await browser.close()
                add_log("Bot session closed.")
        except Exception as e:
            add_log(f"Error in Playwright bot: {str(e)}")
            session_data["status"] = "error"

    def leave_teams_meeting(self, session_id: str) -> Dict[str, Any]:
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
            return {"success": True, "message": "Bot left the meeting."}
        return {"success": False, "error": "Session not found."}
