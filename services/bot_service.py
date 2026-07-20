import os
import logging
import asyncio
import re
import tempfile
from typing import Dict, Any, Optional

logger = logging.getLogger("mom_ai.bot")

def _ensure_black_y4m_file() -> str:
    """Generates a 320x240 solid black Y4M video frame file dynamically at runtime."""
    tmp_dir = tempfile.gettempdir()
    y4m_path = os.path.join(tmp_dir, "black_stream.y4m")
    if not os.path.exists(y4m_path):
        try:
            w, h = 320, 240
            header = f'YUV4MPEG2 W{w} H{h} F30:1 Ip A1:1 C420jpeg\nFRAME\n'.encode('ascii')
            y_plane = bytes([16]) * (w * h)
            u_plane = bytes([128]) * ((w // 2) * (h // 2))
            v_plane = bytes([128]) * ((w // 2) * (h // 2))
            with open(y4m_path, 'wb') as f:
                f.write(header + y_plane + u_plane + v_plane)
        except Exception as e:
            logger.error(f"Failed to generate black.y4m file: {e}")
    return y4m_path

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

            black_y4m_path = _ensure_black_y4m_file()

            async with async_playwright() as p:
                add_log("Launching Chromium browser with black video stream...")
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        "--use-fake-ui-for-media-stream",
                        "--use-fake-device-for-media-stream",
                        f"--use-file-for-fake-video-capture={black_y4m_path}",
                        "--use-file-for-fake-audio-capture=/dev/null",
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

                add_log(f"Navigating to Teams URL...")
                session_data["status"] = "navigating"
                await page.goto(meeting_url, wait_until="domcontentloaded", timeout=40000)
                await page.wait_for_timeout(4000)

                # 1. Bypass "Continue on this browser" / "Use Teams on the web" launcher
                add_log("Bypassing launcher prompts...")
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

                # 2. Turn OFF Camera & Mute Microphone via JS DOM manipulation
                add_log("Turning OFF camera & muting mic in Teams pre-join...")
                try:
                    await page.evaluate("""
                        () => {
                            // Turn off camera toggle
                            const camBtns = Array.from(document.querySelectorAll('div[data-tid="toggle-video"], button[data-tid="video-toggle"], div[role="checkbox"]'));
                            camBtns.forEach(b => {
                                const checked = b.getAttribute('aria-checked');
                                if (checked === 'true' || checked === null) {
                                    b.click();
                                }
                            });
                            // Mute mic toggle
                            const micBtns = Array.from(document.querySelectorAll('div[data-tid="toggle-mute"], button[data-tid="microphone-toggle"]'));
                            micBtns.forEach(b => {
                                const checked = b.getAttribute('aria-checked');
                                if (checked === 'true' || checked === null) {
                                    b.click();
                                }
                            });
                        }
                    """)
                except Exception:
                    pass

                await page.wait_for_timeout(1000)

                # 3. Enter Guest Name
                add_log("Filling Guest Name...")
                session_data["status"] = "entering_name"

                name_selectors = [
                    "input#username",
                    "input[aria-label*='Enter name']",
                    "input[aria-label*='name']",
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

                # 4. Explicitly Locate and Click 'Join Now'
                add_log("Attempting to click 'Join Now' button...")
                session_data["status"] = "joining_call"

                join_clicked = False
                join_selectors = [
                    "button#join-now",
                    "button[data-tid='prejoin-join-button']",
                    "button:has-text('Join now')",
                    "button:has-text('Join')",
                    "div[role='button']:has-text('Join now')",
                    "div[role='button']:has-text('Join')",
                    "button.join-btn"
                ]

                for attempt in range(5):
                    # Try JS click first
                    try:
                        res = await page.evaluate("""
                            () => {
                                const btns = Array.from(document.querySelectorAll('button, div[role="button"]'));
                                const jBtn = btns.find(b => b.innerText && b.innerText.toLowerCase().includes('join'));
                                if (jBtn) {
                                    jBtn.click();
                                    return true;
                                }
                                return false;
                            }
                        """)
                        if res:
                            add_log("JS clicked 'Join' button successfully.")
                            join_clicked = True
                            break
                    except Exception:
                        pass

                    # Try Playwright selector click
                    for sel in join_selectors:
                        try:
                            btn = page.locator(sel).first
                            if await btn.is_visible(timeout=1500):
                                await btn.click(force=True)
                                add_log(f"Playwright clicked 'Join' using selector: {sel}")
                                join_clicked = True
                                break
                        except Exception:
                            continue

                    if join_clicked:
                        break
                    await page.wait_for_timeout(2000)

                if join_clicked:
                    add_log("Join request dispatched! Bot is waiting in Teams lobby/call.")
                    session_data["status"] = "waiting_in_lobby_or_joined"
                else:
                    page_title = await page.title()
                    add_log(f"Could not locate Join button. Current page title: '{page_title}'")
                    session_data["status"] = "error"

                # Keep session active if joined
                while session_id in self.active_sessions and session_data["status"] != "error":
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
