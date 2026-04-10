from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, Response
import requests
import os
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()

# Configs from .env
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN") or os.getenv("ACCESS_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OLLAMA_BASE_URL = (os.getenv("OLLAMA_BASE_URL") or "http://127.0.0.1:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL") or "llama3.2"

# Configure Gemini (skip if no key — Ollama-only mode)
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

app = FastAPI()


@app.get("/ping")
async def ping():
    return {"status": "ok", "service": "whatsapp_agent"}


@app.head("/privacy")
async def privacy_policy_head():
    """Meta and other validators often use HEAD; without this, FastAPI returns 405 and URL looks 'invalid'."""
    return Response(status_code=200, media_type="text/html; charset=utf-8")


@app.get("/privacy", response_class=HTMLResponse)
async def privacy_policy():
    """Public privacy policy page for app store / Meta WhatsApp configuration."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Privacy Policy — Spheretech_AI</title>
  <style>
    body { font-family: system-ui, sans-serif; max-width: 42rem; margin: 2rem auto; padding: 0 1rem; line-height: 1.5; color: #1a1a1a; }
    h1 { font-size: 1.5rem; }
    h2 { font-size: 1.1rem; margin-top: 1.5rem; }
    footer { margin-top: 2rem; font-size: 0.9rem; color: #555; }
  </style>
</head>
<body>
  <h1>Privacy Policy</h1>
  <p><strong>Spheretech_AI</strong> (“we”, “us”) operates this WhatsApp automation service.</p>
  <p><strong>Last updated:</strong> April 10, 2026</p>

  <h2>Information we process</h2>
  <p>When you message our WhatsApp business number, we may process your phone number (as provided by WhatsApp),
  message content, and delivery metadata needed to reply to you.</p>

  <h2>How we use it</h2>
  <p>We use this information to operate the assistant, respond to requests, and improve reliability of the service.
  We do not sell your personal information.</p>

  <h2>Third parties</h2>
  <p>Messages are delivered through <strong>WhatsApp</strong> and related Meta services, subject to their terms and policies.
  Automated replies may use providers such as <strong>Google (Gemini)</strong> or other AI services you configure;
  only content required to generate a reply is sent to those providers.</p>

  <h2>Retention</h2>
  <p>We retain data only as long as needed for the purposes above or as required by law. Contact us to ask about deletion  where applicable.</p>

  <h2>Contact</h2>
  <p>Email: <a href="mailto:spheretechai@gmail.com">spheretechai@gmail.com</a></p>

  <footer>This page is provided for transparency. Review with legal counsel before production use.</footer>
</body>
</html>"""


@app.head("/terms")
async def terms_head():
    return Response(status_code=200, media_type="text/html; charset=utf-8")


@app.get("/terms", response_class=HTMLResponse)
async def terms_of_service():
    """Terms of Service — use as Terms URL in Meta (separate from privacy)."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Terms of Service — Spheretech_AI</title>
  <style>
    body { font-family: system-ui, sans-serif; max-width: 42rem; margin: 2rem auto; padding: 0 1rem; line-height: 1.5; color: #1a1a1a; }
    h1 { font-size: 1.5rem; }
    h2 { font-size: 1.1rem; margin-top: 1.5rem; }
    footer { margin-top: 2rem; font-size: 0.9rem; color: #555; }
  </style>
</head>
<body>
  <h1>Terms of Service</h1>
  <p><strong>Spheretech_AI</strong> — WhatsApp automation assistant.</p>
  <p><strong>Last updated:</strong> April 10, 2026</p>

  <h2>Service</h2>
  <p>The service provides automated messaging and related features via WhatsApp. We may change or discontinue features with reasonable notice where practicable.</p>

  <h2>Acceptable use</h2>
  <p>You agree not to misuse the service, violate applicable law, or infringe others' rights. WhatsApp and Meta rules also apply.</p>

  <h2>Disclaimer</h2>
  <p>The service is provided “as is”. Automated replies may be inaccurate; verify important information independently.</p>

  <h2>Contact</h2>
  <p>Email: <a href="mailto:spheretechai@gmail.com">spheretechai@gmail.com</a></p>

  <footer>Review with legal counsel before production use.</footer>
</body>
</html>"""


# -----------------------------
# Consultant prompt (Gemini + Ollama)
# -----------------------------
def consultant_prompt(user_msg: str) -> str:
    return f"""
You are Spheretech_AI's WhatsApp automation consultant.

About company:
- AI Agents • Workflow Automation • Business Innovation
- We automate operations, workflows, and decisions, not just conversations.
- Focus outcomes: reduce manual work, lower errors, speed up processes, and scale operations.

Capabilities:
- Repetitive task automation
- Workflow management across steps
- Data analysis for operational decisions
- Action triggers from business events
- Tool integrations across existing systems

Industry solutions:
- Business: sales, invoicing, CRM automation
- Schools: admissions, student data, reporting
- Healthcare: scheduling, records, follow-ups

Implementation process:
1) Analyze workflow
2) Design AI agent
3) Integrate systems
4) Automate operations

Pricing (INR):
- Starter: Rs 5,899
- Business: Rs 9,899
- Custom: Talk to us

Contact details:
- Email: spheretechai@gmail.com
- Phone: +91 95209 14146
- WhatsApp: +91 63994 80901

Response rules:
- Be concise, professional, and action-oriented.
- Prioritize business automation guidance and next steps.
- Offer clear CTAs like "Book a demo" or "Share your workflow details" when appropriate.
- If asked unrelated/general-knowledge questions, politely redirect to Spheretech_AI services.
- If details are missing, ask focused clarification questions.
- Do not invent pricing, guarantees, or unsupported technical claims.

User message:
{user_msg}
"""


def ask_gemini(user_msg: str) -> str | None:
    if not GEMINI_API_KEY:
        return None
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(consultant_prompt(user_msg))
        text = (response.text or "").strip()
        return text or None
    except Exception as e:
        print("Gemini Error:", e)
        return None


def ask_ollama(user_msg: str) -> str | None:
    url = f"{OLLAMA_BASE_URL}/api/chat"
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [{"role": "user", "content": consultant_prompt(user_msg)}],
        "stream": False,
    }
    try:
        r = requests.post(url, json=payload, timeout=(10, 120))
        r.raise_for_status()
        data = r.json()
        msg = data.get("message") or {}
        text = (msg.get("content") or "").strip()
        return text or None
    except Exception as e:
        print("Ollama Error:", e)
        return None


def ask_consultant_llm(user_msg: str) -> str:
    reply = ask_gemini(user_msg)
    if reply:
        return reply
    reply = ask_ollama(user_msg)
    if reply:
        return reply
    return "Sorry, I'm having trouble right now. Please try again later."

# -----------------------------
# WhatsApp Send Message
# -----------------------------
def send_whatsapp_message(to, text):
    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"

    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }

    data = {
        "messaging_product": "whatsapp",
        "to": to,
        "text": {"body": text}
    }

    try:
        requests.post(url, headers=headers, json=data)
    except Exception as e:
        print("Send Error:", e)

# -----------------------------
# Intent Detection
# -----------------------------
def detect_intent(msg):
    msg = msg.lower()

    if any(x in msg for x in ["hi", "hello", "hey"]):
        return "greeting"
    elif any(x in msg for x in ["price", "cost", "pricing"]):
        return "pricing"
    elif any(x in msg for x in ["demo", "book", "meeting"]):
        return "demo"
    elif any(x in msg for x in ["service", "what do you do", "automation"]):
        return "services"
    elif any(x in msg for x in ["human", "agent", "call", "contact"]):
        return "human"
    else:
        return "fallback"

# -----------------------------
# Message Handler
# -----------------------------
def handle_message(user_msg, sender):
    intent = detect_intent(user_msg)

    # GREETING MENU
    if intent == "greeting":
        return """Hi 👋 Welcome to Spheretech_AI

We help businesses automate workflows using AI agents.

What would you like to do?

1️⃣ Explore automation solutions  
2️⃣ See pricing  
3️⃣ Book a demo  
4️⃣ Talk to our team
"""

    # PRICING
    elif intent == "pricing":
        return """💰 Pricing Plans:

Starter – ₹5,899  
Business – ₹9,899  
Custom – Based on your requirements  

Would you like help choosing the right plan?
"""

    # SERVICES
    elif intent == "services":
        return """⚙️ Our Capabilities:

• AI Agents for workflow automation  
• CRM & sales automation  
• Scheduling & operations automation  
• Custom integrations across tools  

Which area are you interested in?
"""

    # DEMO BOOKING
    elif intent == "demo":
        return """📅 Great! Let's book your demo.

Please share:
- Your Name  
- Business Type  
- Preferred Time  

Our team will contact you shortly.
"""

    # HUMAN ESCALATION
    elif intent == "human":
        return """👨‍💻 You can directly contact our team:

📞 +91 95209 14146  
📧 spheretechai@gmail.com  

Or continue here — we'll assist you!
"""

    # FALLBACK → Gemini, then Ollama
    else:
        return ask_consultant_llm(user_msg)

# Webhook Verification
# -----------------------------
@app.get("/webhook")
async def verify(request: Request):
    """Meta requires HTTP 200 with hub.challenge echoed as plain text (not JSON)."""
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if (
        mode == "subscribe"
        and VERIFY_TOKEN
        and token == VERIFY_TOKEN
        and challenge is not None
    ):
        return PlainTextResponse(content=challenge)

    return PlainTextResponse(content="Forbidden", status_code=403)

# -----------------------------
# Receive Messages
# ----------------------------
@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()

    try:
        entry = data.get("entry", [])
        for e in entry:
            changes = e.get("changes", [])
            for change in changes:
                value = change.get("value", {})
                messages = value.get("messages")

                if messages:
                    msg = messages[0]
                    user_msg = msg["text"]["body"]
                    sender = msg["from"]

                    print(f"User ({sender}): {user_msg}")

                    reply = handle_message(user_msg, sender)

                    print(f"Bot: {reply}")

                    send_whatsapp_message(sender, reply)

    except Exception as e:
        print("Webhook Error:", e)

    return {"status": "ok"}
