import os
import json
import logging
import asyncio
from typing import List, Dict, Any

from fastapi import FastAPI, Request, BackgroundTasks
from pydantic import BaseModel
import google.generativeai as genai
from playwright.async_api import async_playwright
import requests
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ALLOWED_USER_ID = os.getenv("ALLOWED_USER_ID")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI App
app = FastAPI()

# Gemini Setup
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# Models
class TelegramUpdate(BaseModel):
    update_id: int
    message: Dict[str, Any] = None

# --- Gemini Logic ---
async def parse_instruction_with_gemini(instruction: str) -> List[Dict[str, Any]]:
    """Converts natural language to structured browser actions."""
    prompt = f"""
    You are a browser automation expert. Convert this instruction into a JSON list of browser actions.
    Instruction: "{instruction}"
    
    Allowed actions:
    - {{"action": "navigate", "value": "url"}}
    - {{"action": "click", "selector": "css_selector"}}
    - {{"action": "type", "selector": "css_selector", "value": "text"}}
    - {{"action": "press", "value": "key"}}
    - {{"action": "wait", "value": "seconds"}}
    - {{"action": "screenshot", "value": "filename_suffix"}}
    
    Return ONLY the JSON. Example:
    [{{"action": "navigate", "value": "https://google.com"}}, {{"action": "screenshot", "value": "home"}}]
    """
    try:
        response = await model.generate_content_async(prompt)
        text = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(text)
    except Exception as e:
        logger.error(f"Gemini Error: {e}")
        return []

# --- Playwright Logic ---
async def execute_browser_actions(actions: List[Dict[str, Any]]) -> str:
    """Executes actions and returns the path to the final screenshot."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        last_screenshot = None
        
        try:
            for action in actions:
                act_type = action.get("action")
                val = action.get("value")
                sel = action.get("selector")
                
                if act_type == "navigate":
                    await page.goto(val)
                elif act_type == "click":
                    await page.click(sel)
                elif act_type == "type":
                    await page.fill(sel, val)
                elif act_type == "press":
                    await page.keyboard.press(val)
                elif act_type == "wait":
                    await page.wait_for_timeout(int(val) * 1000)
                elif act_type == "screenshot":
                    # We will take a final screenshot anyway, but process explicit ones too
                    path = f"screenshot_{val}.png"
                    await page.screenshot(path=path)
                    last_screenshot = path
            
            # Always take a final result screenshot
            final_shot = "final_result.png"
            await page.screenshot(path=final_shot)
            last_screenshot = final_shot
            
        except Exception as e:
            logger.error(f"Browser Error: {e}")
            await page.screenshot(path="error.png")
            last_screenshot = "error.png"
        finally:
            await browser.close()
            
        return last_screenshot

# --- Telegram Logic ---
def send_telegram_photo(chat_id: int, caption: str, photo_path: str):
    """Sends a photo back to Telegram."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    try:
        with open(photo_path, 'rb') as photo:
            payload = {'chat_id': chat_id, 'caption': caption}
            files = {'photo': photo}
            requests.post(url, data=payload, files=files)
        # Cleanup
        if os.path.exists(photo_path):
            os.remove(photo_path)
    except Exception as e:
        logger.error(f"Telegram Send Error: {e}")

async def process_update(update: TelegramUpdate):
    """Background task to process the message."""
    if not update.message or 'text' not in update.message:
        return

    chat_id = update.message['chat']['id']
    user_id = str(update.message['from']['id'])
    text = update.message['text']

    if ALLOWED_USER_ID and user_id != ALLOWED_USER_ID:
        requests.get(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage?chat_id={chat_id}&text=Unauthorized")
        return

    # Notify processing
    requests.get(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage?chat_id={chat_id}&text=Processing...")

    # 1. Gemini
    actions = await parse_instruction_with_gemini(text)
    if not actions:
        requests.get(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage?chat_id={chat_id}&text=Could not understand instructions.")
        return

    # 2. Playwright
    screenshot_path = await execute_browser_actions(actions)

    # 3. Respond
    if screenshot_path:
        send_telegram_photo(chat_id, "Task Completed", screenshot_path)
    else:
        requests.get(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage?chat_id={chat_id}&text=Task failed without screenshot.")

# --- Endpoints ---
@app.post("/webhook")
async def telegram_webhook(update: TelegramUpdate, background_tasks: BackgroundTasks):
    """Endpoint receiving Telegram updates."""
    background_tasks.add_task(process_update, update)
    return {"status": "ok"}

@app.get("/")
def health_check():
    return {"status": "running"}
