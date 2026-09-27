from ollama import chat
import requests


def get_weather(city):

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


messages = [
    {
        "role": "user",
        "content": "What is the weather in tunis?"
    }
]

response = chat(
    model="qwen3:14b",
    messages=messages,
    tools=[get_weather]
)

if response.message.tool_calls:

    tool_request = response.message.tool_calls[0]

    result = get_weather(
        tool_request.function.arguments["city"]
    )


    messages.append(response.message)
    messages.append({
        "role": "tool",
        "tool_name": "get_weather",
        "content": result
    })
    final_response = chat(
        model="qwen3:14b",
        messages=messages
    )

    print(final_response.message.content)