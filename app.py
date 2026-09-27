from flask import Flask, render_template, request, jsonify
from ollama import chat
import requests

app = Flask(__name__)

MODEL_NAME = "qwen3:14b"

# In-memory conversation history (simple, resets on server restart)
messages = [
    {
        "role": "system",
        "content": (
            "You are a helpful weather assistant. When the user asks about "
            "weather, use the get_weather tool. Give natural, friendly advice "
            "based on the data (clothing tips, umbrella, etc), not just raw numbers."
        ),
    }
]


def get_weather(city):
    """Get the current temperature for a given city."""

    url = "https://geocoding-api.open-meteo.com/v1/search?name=" + city + "&count=1"
    response = requests.get(url)
    data = response.json()

    if "results" not in data:
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

    weather_response = requests.get(weather_url)
    weather_data = weather_response.json()
    temperature = weather_data["current"]["temperature_2m"]

    return str(temperature) + "°C"


def get_agent_response(user_message: str) -> str:
    messages.append({"role": "user", "content": user_message})

    response = chat(
        model=MODEL_NAME,
        messages=messages,
        tools=[get_weather],
    )

    if response.message.tool_calls:
        tool_request = response.message.tool_calls[0]

        result = get_weather(tool_request.function.arguments["city"])

        print(f"[DEBUG] tool call -> get_weather({tool_request.function.arguments})")
        print(f"[DEBUG] tool result -> {result}")

        messages.append(response.message)
        messages.append({
            "role": "tool",
            "tool_name": "get_weather",
            "content": result,
        })

        final_response = chat(model=MODEL_NAME, messages=messages)
        reply = final_response.message.content
        messages.append({"role": "assistant", "content": reply})
        return reply

    reply = response.message.content
    messages.append({"role": "assistant", "content": reply})
    return reply


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat_route():
    user_message = request.json.get("message", "").strip()
    if not user_message:
        return jsonify({"reply": "Please type something."}), 400

    try:
        reply = get_agent_response(user_message)
    except Exception as e:
        print(f"[DEBUG] EXCEPTION -> {e}")
        reply = f"Sorry, something went wrong: {e}"

    return jsonify({"reply": reply})


if __name__ == "__main__":
    app.run(debug=True)