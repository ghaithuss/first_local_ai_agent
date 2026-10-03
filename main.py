from ollama import chat
import os
import requests
import webbrowser
from dotenv import load_dotenv
load_dotenv()  
from tavily import TavilyClient
tavily_client = TavilyClient(api_key=os.getenv("Tavily_API_KEY"))

def get_weather(city):
    """get the current temperature for a city eg:tunis """
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


def open_website(url):
    """
    Open a website URL in the user's default browser.
    Use this after obtaining a valid URL from the user or from google_search.
    """

    confirmation = ""

    while confirmation.lower() not in ["y", "n"]:
        confirmation = input("Are you sure you want to open " + url + "? (y/n): ")

    if confirmation.lower() == "y":
        webbrowser.open(url)
        return "successfully opened"

    return "operation cancelled"

def google_search(query):
    """
    Search the web for websites, companies, products, people, or information.
    Use this whenever the user asks to find a website, company, or information online.
    Returns search results with titles and URLs.
    """
    response=tavily_client.search(query)
    result=response["results"]
    if not result:
        return "No results found"
    output=""
    for item in result:
        output+="url: "+item["url"]+"  "+ "title: "+item["title"]+"\n"
    return output
            

    


messages = [
    {
        "role": "user",
        "content": "can u open the official tunisian website of mytek and navigate to the pc gaming section because i want to buy a new pc gaming and gimme an advicce about the best pc gaming to buy in 2026"
        
    }
]


while True:

    response = chat(
        model="qwen3:8b",
        messages=messages,
        tools=[get_weather, open_website,google_search]
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

        print(response.message.content)

        break
