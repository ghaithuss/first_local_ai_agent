from dotenv import load_dotenv
load_dotenv()  # must run before reading any env variable

import os
import webbrowser
import requests
from flask import Flask, render_template, request, jsonify
from ollama import chat
from tavily import TavilyClient

app = Flask(__name__)

MODEL_NAME = "qwen3:8b"       
CHAT_OPTIONS = {"num_ctx": 4096}
MAX_HISTORY = 20
MAX_TOOL_ROUNDS = 5

tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

SYSTEM_PROMPT = {
    "role": "system",
    "content": (
        "You are JaRvis, a smart, friendly personal assistant running on the user's own computer. "
        "You CAN open websites for the user using your tools. Never say you can't browse or open links. "
        "Tools: get_weather (current weather of a city), google_search (find websites and info online), "
        "open_website (opens a URL in the user's browser). "
        "To open a website: first call google_search, pick the official URL from the results, "
        "then call open_website with that URL. "
        "Always use the tool-calling mechanism, never write JSON in your reply. "
        "Be concise and natural, and give practical advice, not just raw data."
    ),
}

messages = [SYSTEM_PROMPT]


# ---------- Tools ----------

def get_weather(city: str) -> str:
    """Get the current temperature, rain and wind for a city, e.g. Tunis."""
    try:
        geo = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": city, "count": 1},
            timeout=10,
        ).json()
        if not geo.get("results"):
            return "City not found"
        place = geo["results"][0]
        w = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": place["latitude"],
                "longitude": place["longitude"],
                "current": "temperature_2m,precipitation,wind_speed_10m",
            },
            timeout=10,
        ).json()["current"]
        return (
            f"{place['name']}: {w['temperature_2m']}°C, "
            f"precipitation {w['precipitation']} mm, wind {w['wind_speed_10m']} km/h"
        )
    except requests.RequestException as e:
        return f"Weather service error: {e}"


def google_search(query: str) -> str:
    """Search the web for websites, companies, products, people or information.
    Use this whenever the user asks to find a website, a product, or anything online.
    Returns results with title, URL and a short summary."""
    try:
        res = tavily_client.search(query, max_results=4)
    except Exception as e:
        return f"Search error: {e}"
    results = res.get("results", [])
    if not results:
        return "No results found"
    out = ""
    for item in results:
        out += f"title: {item['title']}\nurl: {item['url']}\ncontent: {item['content'][:300]}\n\n"
    return out


def open_website(url: str) -> str:
    """Open a website URL in the user's default browser.
    Use this after getting a valid URL from google_search or from the user."""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    webbrowser.open(url)
    return f"Opened {url} in the browser"


TOOLS = {
    "get_weather": get_weather,
    "google_search": google_search,
    "open_website": open_website,
}


# ---------- Agent loop ----------

def ask_model(use_tools=True):
    return chat(
        model=MODEL_NAME,
        messages=messages,
        tools=list(TOOLS.values()) if use_tools else None,
        think=False,
        options=CHAT_OPTIONS,
    )


def get_agent_response(user_message: str) -> str:
    global messages
    start_len = len(messages)
    messages.append({"role": "user", "content": user_message})

    try:
        response = ask_model()
        rounds = 0

        while response.message.tool_calls and rounds < MAX_TOOL_ROUNDS:
            rounds += 1
            messages.append(response.message)

            for call in response.message.tool_calls:
                name = call.function.name
                args = call.function.arguments
                fn = TOOLS.get(name)
                try:
                    result = fn(**args) if fn else f"Unknown tool: {name}"
                except Exception as e:
                    result = f"Tool error: {e}"

                print(f"[DEBUG] tool call -> {name}({args})")
                print(f"[DEBUG] tool result -> {str(result)[:200]}")
                messages.append({"role": "tool", "tool_name": name, "content": str(result)})

            response = ask_model()

        reply = response.message.content or "Done."
        messages.append({"role": "assistant", "content": reply})

        # Trim old history, always starting from a user message
        if len(messages) > MAX_HISTORY + 1:
            recent = messages[-MAX_HISTORY:]
            while recent and not (isinstance(recent[0], dict) and recent[0].get("role") == "user"):
                recent = recent[1:]
            messages = [SYSTEM_PROMPT] + recent

        return reply

    except Exception:
        del messages[start_len:]
        raise


# ---------- Routes ----------

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat_route():
    user_message = (request.json or {}).get("message", "").strip()
    if not user_message:
        return jsonify({"reply": "Please type something."}), 400
    try:
        reply = get_agent_response(user_message)
    except Exception as e:
        print(f"[DEBUG] EXCEPTION -> {e}")
        return jsonify({"reply": f"Something went wrong: {e}"}), 500
    return jsonify({"reply": reply})


@app.route("/reset", methods=["POST"])
def reset():
    global messages
    messages = [SYSTEM_PROMPT]
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)