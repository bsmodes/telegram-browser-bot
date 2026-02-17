# FastAPI Telegram-Gemini Browser Bot

A "Plug and Play" Dockerized Telegram bot that uses Google Gemini to control a headless Playwright browser.

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/bsmodes/telegram-browser-bot)

## Features
- **FastAPI Webhook**: Efficiently handles Telegram updates.
- **Gemini Reasoning**: Converts natural language into JSON browser actions.
- **Playwright Execution**: Runs actions headlessly and captures screenshots.
- **Docker Ready**: Deploy anywhere with a single command.

## Quick Start (Docker)

1.  **Clone & Configure**
    ```bash
    cp .env.example .env
    # Edit .env with your TELEGRAM_BOT_TOKEN and GEMINI_API_KEY
    ```

2.  **Build & Run**
    ```bash
    docker build -t telegram-browser-bot .
    docker run -d -p 8080:8080 --env-file .env telegram-browser-bot
    ```

3.  **Set Webhook**
    ```bash
    curl -F "url=https://your-domain.com/webhook" https://api.telegram.org/bot<YOUR_TOKEN>/setWebhook
    ```

## Local Development

1.  **Install**
    ```bash
    pip install -r requirements.txt
    playwright install
    ```

2.  **Run**
    ```bash
    uvicorn main:app --reload
    ```

3.  **Expose Locally**
    Use `ngrok` to expose port 8000:
    ```bash
    ngrok http 8000
    ```
    Then set your Telegram webhook to the ngrok URL.

## Usage
Send a message like:
> "Go to google.com, search for 'FastAPI', and take a screenshot."

The bot will perform the actions and reply with a screenshot.
