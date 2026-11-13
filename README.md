# 🤖 JaRvis: Local AI Agent

A personal AI assistant that runs **locally on your computer** with [Ollama](https://ollama.com) and the **Qwen3 8B** model. JaRvis talks to you through a simple web chat and can call real tools to get things done.

## ✨ Features

- 🔍 **Web search**: finds up-to-date information with the Tavily API
- 🌤️ **Weather**: current temperature for any city (Open-Meteo, no key needed)
- 🌐 **Open websites**: finds the official URL and opens it in your browser, **only after you confirm**
- 💬 **Web chat UI** built with Flask, with conversation memory and a reset button
- 🔒 **Private**: the language model runs on your machine, not in the cloud

## 🧠 How it works

```
User ──► Flask web UI ──► Agent loop (Qwen3 via Ollama)
                              │
                              ├── get_weather(city)    → Open-Meteo API
                              ├── google_search(query) → Tavily API
                              └── open_website(url)    → asks user to confirm → browser
```

The agent uses **tool calling**. The model decides which tool to use, the app runs it and sends back the result, and the loop repeats for up to 5 rounds until the model gives a final answer.

## 🛠️ Tech Stack

Python · Flask · Ollama · Qwen3 8B · Tavily API · Open-Meteo API

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.10+
- [Ollama](https://ollama.com/download) installed and running
- A free [Tavily API key](https://tavily.com)

### 2. Install
```bash
git clone https://github.com/ghaithuss/first_local_ai_agent.git
cd first_local_ai_agent
pip install -r requirements.txt
ollama pull qwen3:8b
```

### 3. Configure
Create a `.env` file in the project folder:
```
TAVILY_API_KEY=your_api_key_here
```

### 4. Run
```bash
python app.py
```
Then open **http://127.0.0.1:5000** in your browser.

> `main.py` is the first command-line version of the agent, kept for reference.

## 💡 Example prompts

- "What's the weather in Tunis?"
- "Search for the latest news about AI agents."
- "Open the official Mytek website."

## 🗺️ Roadmap

- [ ] Voice input and output
- [ ] More tools (calendar, notes, file search)
- [ ] Streaming responses in the chat UI

## 👤 Author

**Ghaith Hbibi**: [GitHub](https://github.com/ghaithuss) · [LinkedIn](https://linkedin.com/in/ghaith-hbibi-672b62340)
