import logging
import asyncio
import re
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
            "message": f"Bot '{bot_name}' is launching Chromium to join Teams meeting."
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
                add_log("Launching Chromium browser...")
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        "--use-fake-ui-for-media-stream",
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

                add_log("Navigating to Teams meeting URL...")
                session_data["status"] = "navigating"
                await page.goto(meeting_url, wait_until="domcontentloaded", timeout=35000)
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

                for sel in continue_selectors:
                    try:
                        btn = page.locator(sel).first
                        if await btn.is_visible(timeout=2000):
                            await btn.click()
                            add_log("Clicked 'Continue on browser'")
                            break
                    except Exception:
                        continue

                await page.wait_for_timeout(5000)

                # 2. Turn OFF Camera & Mute Microphone
                add_log("Turning OFF camera & muting mic...")
                camera_toggles = [
                    "div[data-tid='toggle-video']",
                    "button[data-tid='video-toggle']",
                    "div[role='checkbox'][aria-label*='camera']",
                    "div[role='checkbox'][aria-label*='video']",
                    "button[aria-label*='camera']"
                ]
                for sel in camera_toggles:
                    try:
                        tgl = page.locator(sel).first
                        if await tgl.is_visible(timeout=1500):
                            await tgl.click()
                            add_log("Toggled camera off.")
                            break
                    except Exception:
                        continue

                mic_toggles = [
                    "div[data-tid='toggle-mute']",
                    "button[data-tid='microphone-toggle']",
                    "div[role='checkbox'][aria-label*='mic']",
                    "div[role='checkbox'][aria-label*='mute']",
                    "button[aria-label*='mic']"
                ]
                for sel in mic_toggles:
                    try:
                        tgl = page.locator(sel).first
                        if await tgl.is_visible(timeout=1500):
                            await tgl.click()
                            add_log("Toggled mic muted.")
                            break
                    except Exception:
                        continue

                # 3. Enter Guest Name
                add_log("Entering Guest Name...")
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

                for sel in name_selectors:
                    try:
                        inp = page.locator(sel).first
                        if await inp.is_visible(timeout=2500):
                            await inp.fill(bot_name)
                            add_log(f"Filled Guest Name '{bot_name}'")
                            break
                    except Exception:
                        continue

                await page.wait_for_timeout(2000)

                # 4. Explicitly Find & Click 'Join Now' Button
                add_log("Clicking 'Join Now' button...")
                session_data["status"] = "joining_call"

                join_selectors = [
                    "button#join-now",
                    "button[data-tid='prejoin-join-button']",
                    "button:has-text('Join now')",
                    "button:has-text('Join')",
                    "div[role='button']:has-text('Join now')",
                    "div[role='button']:has-text('Join')",
                    "button.join-btn"
                ]

                clicked_join = False
                for retry in range(5):
                    for sel in join_selectors:
                        try:
                            btn = page.locator(sel).first
                            if await btn.is_visible(timeout=2000):
                                await btn.click()
                                add_log(f"Successfully clicked 'Join now' ({sel})!")
                                clicked_join = True
                                break
                        except Exception:
                            continue
                    if clicked_join:
                        break
                    await page.wait_for_timeout(2000)

                if clicked_join:
                    session_data["status"] = "waiting_in_lobby_or_joined"
                    add_log("Join request sent! Bot is waiting in Teams lobby/call.")
                else:
                    session_data["status"] = "error"
                    add_log("Failed to locate 'Join now' button on Teams pre-join page.")

                # Keep session active
                while session_id in self.active_sessions:
                    await asyncio.sleep(2)

                await browser.close()
                add_log("Bot session ended.")
        except Exception as e:
            add_log(f"Error in Playwright bot: {str(e)}")
            session_data["status"] = "error"

    def leave_teams_meeting(self, session_id: str) -> Dict[str, Any]:
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
            return {"success": True, "message": "Bot left the meeting."}
        return {"success": False, "error": "Session not found."}
