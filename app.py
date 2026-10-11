
from dotenv import load_dotenv
load_dotenv()

from ollama import chat
import os
import requests
import webbrowser
from flask import Flask, render_template, request, jsonify
from tavily import TavilyClient

app = Flask(__name__)

tavily_client = TavilyClient(
    api_key=os.getenv("TAVILY_API_KEY")
)


# ---------- Tools ----------

def get_weather(city):
    """Get the current temperature for a city, e.g. Tunis."""

    try:
        url = "https://geocoding-api.open-meteo.com/v1/search?name=" + city + "&count=1"

        response = requests.get(url, timeout=10)
        data = response.json()

        if "results" not in data or not data["results"]:
            return "City not found"

        city_data = data["results"][0]

        latitude = city_data["latitude"]
        longitude = city_data["longitude"]

        weather_url = (
            "https://api.open-meteo.com/v1/forecast"
            + "?latitude=" + str(latitude)
            + "&longitude=" + str(longitude)
            + "&current=temperature_2m"
        )

        weather_response = requests.get(weather_url, timeout=10)
        weather_data = weather_response.json()

        temperature = weather_data["current"]["temperature_2m"]

        return str(temperature) + "°C"

    except Exception as e:
        return "Weather error: " + str(e)


def google_search(query):
    """Search the web for websites, products and information."""

    try:
        response = tavily_client.search(query, max_results=4)
        result = response["results"]

        if not result:
            return "No results found"

        output = ""

        for item in result:
            output += "url: " + item["url"] + "\n"
            output += "title: " + item["title"] + "\n"
            output += "content: " + item.get("content", "")[:300] + "\n\n"

        return output

    except Exception as e:
        return "Search error: " + str(e)


def open_website(url):
    """Open a website in the user's browser."""

    if not url.startswith(("http://", "https://")):
        return "Invalid URL"

    webbrowser.open(url)

    return "Successfully opened " + url


# ---------- Tools List ----------

TOOLS = {
    "get_weather": get_weather,
    "google_search": google_search,
    "open_website": open_website
}


# ---------- AI Agent ----------

SYSTEM_PROMPT = {
    "role": "system",
    "content": (
        "You are JaRvis, a friendly personal AI assistant running locally "
        "on the user's computer. "
        "You can check weather, search the web and open websites. "
        "Use google_search to find information online. "
        "When asked to open a website, find the official URL first when needed "
        "and then use open_website. "
        "Be concise, natural and helpful."
    )
}

messages = [SYSTEM_PROMPT]


def get_agent_response(user_message):
    global messages

    messages.append({
        "role": "user",
        "content": user_message
    })

    rounds = 0

    while rounds < 5:

        response = chat(
            model="qwen3:8b",
            messages=messages,
            tools=[get_weather, open_website, google_search],
            think=False,
            options={"num_ctx": 4096}
        )

        if response.message.tool_calls:

            messages.append(response.message)

            for tool_call in response.message.tool_calls:

                if tool_call.function.name == "get_weather":

                    city = tool_call.function.arguments["city"]
                    result = get_weather(city)

                    messages.append({
                        "role": "tool",
                        "tool_name": "get_weather",
                        "content": result
                    })

                elif tool_call.function.name == "open_website":

                    site = tool_call.function.arguments["url"]
                    result = open_website(site)

                    messages.append({
                        "role": "tool",
                        "tool_name": "open_website",
                        "content": result
                    })

                elif tool_call.function.name == "google_search":

                    query = tool_call.function.arguments["query"]
                    result = google_search(query)

                    messages.append({
                        "role": "tool",
                        "tool_name": "google_search",
                        "content": result
                    })

                else:

                    messages.append({
                        "role": "tool",
                        "tool_name": tool_call.function.name,
                        "content": "Unknown tool"
                    })

            rounds += 1

        else:

            reply = response.message.content

            messages.append({
                "role": "assistant",
                "content": reply
            })

            if len(messages) > 21:
                messages = [SYSTEM_PROMPT] + messages[-20:]

            return reply

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
        print("Error:", e)

        return jsonify({
            "reply": "Something went wrong. Check the terminal."
        }), 500


@app.route("/reset", methods=["POST"])
def reset():

    global messages
    messages = [SYSTEM_PROMPT]

    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(debug=False, use_reloader=False)
