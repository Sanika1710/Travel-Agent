# Travel Booking Agent

This project is an AI-powered travel assistant that helps users book flights and cabs seamlessly through a conversational interface. The application uses [Streamlit](https://streamlit.io/) for the web UI and integrates with LLMs (via [LangChain](https://python.langchain.com/) and [Groq](https://groq.com/)) to power the flight and cab booking agents.

## Features

- **Conversational Booking:** Book flights and cabs through a chat interface.
- **Smart Supervisor:** Guides the user, routes requests to the right agent, and suggests complementary bookings (e.g., book a cab after a flight).
- **Context Sharing:** Shares booking context between agents for a smooth experience.
- **Modern UI:** Built with Streamlit, featuring a sidebar dashboard and styled chat history.
- **Extensible Agents:** Modular code for flight and cab agents, easy to extend for more services.

## Project Structure

```
main1.py
agents/
    __init__.py
    cab_agent.py
    flight_agent.py
    supervisor_agent.py
    Supervisor_updated.py
```

- `main1.py`: Main Streamlit app.
- `agents/flight_agent.py`: Flight booking agent logic.
- `agents/cab_agent.py`: Cab booking agent logic.
- `agents/supervisor_agent.py`: (Optional) LLM-based supervisor agent.
- `agents/Supervisor_updated.py`: CLI-based supervisor for terminal use.

## Setup Instructions

### 1. Clone the Repository

```sh
git clone https://github.com/Sanika1710/Travel-Agent
cd Travel-Agent
```

### 2. Install Dependencies

It's recommended to use a virtual environment.

```sh
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**Example `requirements.txt`:**
```
streamlit
langchain
langchain_groq
```

You may need to install other dependencies as required by your environment.

### 3. Set Up API Keys

The agents use the Groq API for LLM access. Set your Groq API key as an environment variable:

```sh
export GROQ_API_KEY=your_groq_api_key
```

Or replace `"API KEY"` in the agent files with your actual key (not recommended for production).

### 4. Run the Streamlit App

```sh
streamlit run main1.py
```

The app will open in your browser. You can now chat with the travel agent to book flights and cabs.

## Usage

- Start a conversation by specifying what you want to book (e.g., "I want to book a flight").
- The supervisor will guide you and route your request to the appropriate agent.
- After booking a flight or cab, the supervisor will suggest booking the complementary service.
- You can stop the booking process at any time by typing "stop".

## Notes

- The project is modular; you can extend it by adding more agents or improving prompts.
- For CLI-based interaction, you can run `agents/Supervisor_updated.py` directly:

  ```sh
  python agents/Supervisor_updated.py
  ```

