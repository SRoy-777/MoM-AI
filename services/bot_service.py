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
            "message": f"Bot '{bot_name}' is joining Teams meeting."
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
                add_log("Launching Chromium browser with silent media streams...")
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        "--use-fake-ui-for-media-stream",
                        "--use-fake-device-for-media-stream",
                        "--use-file-for-fake-audio-capture=/dev/null",
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-blink-features=AutomationControlled"
                    ]
                )
                # Only grant microphone, omit camera permission so Teams keeps camera OFF automatically
                context = await browser.new_context(
                    permissions=["microphone"],
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                    viewport={"width": 1280, "height": 720}
                )
                page = await context.new_page()

                add_log("Navigating to Teams meeting URL...")
                session_data["status"] = "navigating"
                await page.goto(meeting_url, wait_until="domcontentloaded", timeout=40000)
                await page.wait_for_timeout(3000)

                # 1. Bypass "Continue on this browser"
                add_log("Bypassing launcher prompts...")
                for sel in [
                    "button#openTeamsInApp",
                    "a[data-tid='joinOnWeb']",
                    "button[data-tid='joinOnWeb']",
                    "button:has-text('Continue on this browser')",
                    "a:has-text('Continue on this browser')",
                    "button:has-text('Use Teams on the web')"
                ]:
                    try:
                        btn = page.locator(sel).first
                        if await btn.is_visible(timeout=1500):
                            await btn.click()
                            add_log("Selected web browser join.")
                            break
                    except Exception:
                        continue

                await page.wait_for_timeout(4000)

                # 2. Enter Guest Name
                add_log("Filling Guest Name...")
                session_data["status"] = "entering_name"

                for sel in [
                    "input#username",
                    "input[aria-label*='Enter name']",
                    "input[aria-label*='name']",
                    "input[placeholder*='name']",
                    "input[data-tid='prejoin-display-name-input']",
                    "input[type='text']"
                ]:
                    try:
                        inp = page.locator(sel).first
                        if await inp.is_visible(timeout=2000):
                            await inp.fill(bot_name)
                            add_log(f"Filled Guest Name '{bot_name}'")
                            break
                    except Exception:
                        continue

                await page.wait_for_timeout(1000)

                # 3. Join Call via Direct Click + JS Event Trigger + Keyboard Enter
                add_log("Triggering Join request...")
                session_data["status"] = "joining_call"

                # Execute JS click + Keyboard Enter + Playwright click simultaneously for maximum reliability
                try:
                    await page.evaluate("""
                        () => {
                            const btns = Array.from(document.querySelectorAll('button, div[role="button"]'));
                            const joinBtn = btns.find(b => b.innerText && b.innerText.toLowerCase().includes('join'));
                            if (joinBtn) {
                                joinBtn.click();
                            }
                        }
                    """)
                except Exception:
                    pass

                join_selectors = [
                    "button#join-now",
                    "button[data-tid='prejoin-join-button']",
                    "button:has-text('Join now')",
                    "button:has-text('Join')",
                    "div[role='button']:has-text('Join now')",
                    "div[role='button']:has-text('Join')"
                ]

                for sel in join_selectors:
                    try:
                        btn = page.locator(sel).first
                        if await btn.is_visible(timeout=1500):
                            await btn.click(force=True)
                            break
                    except Exception:
                        continue

                add_log("Join request dispatched! Bot is active in call / lobby.")
                session_data["status"] = "waiting_in_lobby_or_joined"

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
