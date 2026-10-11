
from dotenv import load_dotenv
load_dotenv()

import os
import requests
import webbrowser
from urllib.parse import urlparse
from flask import Flask, render_template, request, jsonify
from ollama import chat
from tavily import TavilyClient

app = Flask(__name__)

MODEL_NAME = "qwen3:8b"

tavily_client = TavilyClient(
    api_key=os.getenv("TAVILY_API_KEY")
)

pending_url = None

SYSTEM_PROMPT = {
    "role": "system",
    "content": (
        "You are JaRvis, a friendly personal AI assistant running locally "
        "on the user's computer. "
        "You can check weather, search the web and open websites. "
        "Use google_search to find online information. "
        "When asked to open a website, find the official URL first when needed, "
        "then call open_website with that URL. "
        "The application will ask the user for confirmation before opening it. "
        "Be concise, natural and helpful."
    )
}

messages = [SYSTEM_PROMPT]


# ---------- Tools ----------

def get_weather(city):
    """Get the current temperature for a city, e.g. Tunis."""

    try:
        url = "https://geocoding-api.open-meteo.com/v1/search"

        response = requests.get(
            url,
            params={"name": city, "count": 1},
            timeout=10
        )

        data = response.json()

        if not data.get("results"):
            return "City not found"

        city_data = data["results"][0]

        latitude = city_data["latitude"]
        longitude = city_data["longitude"]

        weather_url = "https://api.open-meteo.com/v1/forecast"

        weather_response = requests.get(
            weather_url,
            params={
                "latitude": latitude,
                "longitude": longitude,
                "current": "temperature_2m"
            },
            timeout=10
        )

        weather_data = weather_response.json()
        temperature = weather_data["current"]["temperature_2m"]

        return str(temperature) + "°C"

    except Exception as e:
        return "Weather error: " + str(e)


def google_search(query):
    """Search the web and return titles, URLs and summaries."""

    try:
        response = tavily_client.search(query, max_results=4)
        results = response.get("results", [])

        if not results:
            return "No results found"

        output = ""

        for item in results:
            output += "title: " + item.get("title", "") + "\n"
            output += "url: " + item.get("url", "") + "\n"
            output += "content: " + item.get("content", "")[:300] + "\n\n"

        return output

    except Exception as e:
        return "Search error: " + str(e)


def open_website(url):
    """Request that the application open a website after confirmation."""

    return "Website opening requires user confirmation."


TOOLS = {
    "get_weather": get_weather,
    "google_search": google_search,
    "open_website": open_website
}


# ---------- Agent ----------

def get_agent_response(user_message):
    global messages, pending_url

    messages.append({
        "role": "user",
        "content": user_message
    })

    rounds = 0

    while rounds < 5:

        response = chat(
            model=MODEL_NAME,
            messages=messages,
            tools=[get_weather, google_search, open_website],
            think=False,
            options={"num_ctx": 4096}
        )

        if not response.message.tool_calls:

            reply = response.message.content or "I'm not sure how to answer."

            messages.append({
                "role": "assistant",
                "content": reply
            })

            if len(messages) > 21:
                messages = [SYSTEM_PROMPT] + messages[-20:]

            return reply

        messages.append(response.message)

        for tool_call in response.message.tool_calls:

            name = tool_call.function.name
            arguments = tool_call.function.arguments

            if name == "open_website":

                url = arguments.get("url", "").strip()

                if not url.startswith(("http://", "https://")):
                    url = "https://" + url

                parsed_url = urlparse(url)

                if (
                    parsed_url.scheme not in ("http", "https")
                    or not parsed_url.hostname
                    or parsed_url.username
                    or parsed_url.password
                ):
                    result = "Invalid website URL."

                    messages.append({
                        "role": "tool",
                        "tool_name": name,
                        "content": result
                    })

                    continue

                pending_url = url

                # Complete the tool-call exchange in the conversation.
                messages.append({
                    "role": "tool",
                    "tool_name": name,
                    "content": "Waiting for the user's confirmation to open " + url
                })

                reply = "CONFIRM_OPEN:" + url

                messages.append({
                    "role": "assistant",
                    "content": "Asked the user to confirm opening " + url
                })

                return reply

            if name in TOOLS:
                try:
                    result = TOOLS[name](**arguments)
                except Exception as e:
                    result = "Tool error: " + str(e)
            else:
                result = "Unknown tool: " + name

            messages.append({
                "role": "tool",
                "tool_name": name,
                "content": str(result)
            })

        rounds += 1

    return "I couldn't complete the request. Please try again."


# ---------- Flask Routes ----------

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
        return jsonify({"reply": reply})

    except Exception as e:
        print("Agent error:", e)

        return jsonify({
            "reply": "Something went wrong. Check the terminal."
        }), 500


@app.route("/confirm-open", methods=["POST"])
def confirm_open():
    global pending_url, messages

    answer = (request.json or {}).get("answer", "").lower()

    if answer not in ("y", "n"):
        return jsonify({"reply": "Please choose Yes or No."}), 400

    if pending_url is None:
        return jsonify({
            "reply": "There is no website waiting for confirmation."
        }), 400

    url = pending_url
    pending_url = None

    if answer == "n":
        messages.append({
            "role": "user",
            "content": "I declined to open " + url
        })

        reply = "Opening cancelled."

        messages.append({
            "role": "assistant",
            "content": reply
        })

        return jsonify({"reply": reply})

    try:
        opened = webbrowser.open(url)

        if opened:
            reply = "Successfully opened " + url
        else:
            reply = "The browser did not confirm that it opened the website."

    except Exception as e:
        reply = "Could not open the website: " + str(e)

    messages.append({
        "role": "user",
        "content": "I confirmed opening " + url
    })

    messages.append({
        "role": "assistant",
        "content": reply
    })

    return jsonify({"reply": reply})


@app.route("/reset", methods=["POST"])
def reset():
    global messages, pending_url

    messages = [SYSTEM_PROMPT]
    pending_url = None

    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(debug=False, use_reloader=False)
