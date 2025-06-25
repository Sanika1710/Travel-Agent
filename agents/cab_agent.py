import os
from typing import List, Dict, Any, Optional
from enum import Enum
from datetime import datetime

from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage

# --- Model setup ---
os.environ["GROQ_API_KEY"] = "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"  # Replace with secure method in prod
MODEL = "llama3-70b-8192"
cab_llm = ChatGroq(temperature=0, model_name=MODEL)

# --- Agent states ---
class AgentState(str, Enum):
    CAB_AGENT = "cab_agent"
    END = "end"

# --- Conversation state management ---
class ConversationState:
    def __init__(self):
        self.messages: List[Dict[str, Any]] = []
        self.current_agent: AgentState = AgentState.CAB_AGENT
        self.booking_info: Dict[str, Any] = {
            "cab": {}
        }

    def add_message(self, role: str, content: str, agent: Optional[AgentState] = None):
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "agent": agent if agent else self.current_agent
        })

    def get_conversation_history(self) -> str:
        history = ""
        for msg in self.messages:
            agent_prefix = f"[{msg['agent']}] " if 'agent' in msg else ""
            history += f"{agent_prefix}{msg['role']}: {msg['content']}\n\n"
        return history

    def to_dict(self) -> Dict[str, Any]:
        return {
            "messages": self.messages,
            "current_agent": self.current_agent,
            "booking_info": self.booking_info,
            "user_input": ""
        }

    @classmethod
    def from_dict(cls, state_dict: Dict[str, Any]) -> 'ConversationState':
        state = cls()
        state.messages = state_dict.get("messages", [])
        state.current_agent = state_dict.get("current_agent", AgentState.CAB_AGENT)
        state.booking_info = state_dict.get("booking_info", {"cab": {}})
        return state

# --- Prompt template for Cab Agent ---
CAB_AGENT_PROMPT = """You are a Cab Booking Agent. Your job is to help users book cabs.
Sometimes you might be called after booking a flight and you will be provided with the flight details. In such cases, use the flight information to help the user book a cab either to the departure airport or from the arrival airport to their destination.
You need to collect all necessary information like:
- Pickup location
- Drop-off location
- Date and time of ride
- Number of passengers
- Type of cab (standard, SUV, luxury)
- Any special instructions or preferences

Be friendly and conversational. Follow these steps:

1. Collect all required information from the user (pickup location, drop-off location, date, time, number of passengers, type of cab).
2. Once you have all the details, recap the booking details for the user and ask if there are any special instructions or if they are ready to confirm the booking.
3. Wait for the user to either:
   - Confirm the booking (e.g., by saying "yes", "book it", "confirm", etc.).
   - Provide special instructions (e.g., "I have a special request", "add instructions", etc.).
   - Decline special instructions (e.g., "no special instructions", "no", etc.).
4. If the user confirms the booking or declines special instructions, then confirm the cab booking, inform the user that the cab has been booked, and end your response with: "BOOKING_COMPLETE".
5. If the user provides special instructions, add them to the booking details, recap the updated details, and ask for confirmation again.

IMPORTANT: Do NOT add "BOOKING_COMPLETE" until the user has explicitly confirmed the booking or declined to add special instructions.

Conversation history:
{conversation_history}

User: {user_input}
Cab Agent:"""


def cab_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    state_obj = ConversationState.from_dict(state)
    user_input = state.get("user_input", "")

    prompt = ChatPromptTemplate.from_template(CAB_AGENT_PROMPT)

    messages = [
        SystemMessage(content="You are a helpful Cab Booking Agent assistant."),
        HumanMessage(content=prompt.format(
            conversation_history=state_obj.get_conversation_history(),
            user_input=user_input
        ))
    ]

    response = cab_llm.invoke(messages)

    # Add user message
    state_obj.add_message("user", user_input)
    
    # Process agent response
    agent_response = response.content
    
    # Check if booking is complete
    if "BOOKING_COMPLETE" in agent_response:
        # Clean the response by removing "BOOKING_COMPLETE"
        clean_response = agent_response.replace("BOOKING_COMPLETE", "").strip()
        # Add only the cleaned response
        state_obj.add_message("assistant", clean_response)
        # Update booking info
        state_obj.booking_info["cab"]["status"] = "booked"
        state_obj.booking_info["cab"]["details"] = "Cab booked based on user preferences"
        state_obj.current_agent = AgentState.END
    else:
        # Add the response as-is if booking is not complete
        state_obj.add_message("assistant", agent_response)

    result = state_obj.to_dict()
    result["user_input"] = ""  # Clear input for next step
    return result