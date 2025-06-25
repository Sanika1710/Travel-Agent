import os
from typing import List, Dict, Any, Optional
from enum import Enum
from datetime import datetime

from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage

# --- Model setup ---
os.environ["GROQ_API_KEY"] = "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"  # Replace with env variable in production
MODEL = "llama3-70b-8192"
flight_llm = ChatGroq(temperature=0, model_name=MODEL)

# --- Agent states ---
class AgentState(str, Enum):
    FLIGHT_AGENT = "flight_agent"
    END = "end"

# --- Conversation state management ---
class ConversationState:
    def __init__(self):
        self.messages: List[Dict[str, Any]] = []
        self.current_agent: AgentState = AgentState.FLIGHT_AGENT
        self.booking_info: Dict[str, Any] = {
            "flight": {}
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
        state.current_agent = state_dict.get("current_agent", AgentState.FLIGHT_AGENT)
        state.booking_info = state_dict.get("booking_info", {"flight": {}})
        return state

# --- Prompt template ---
FLIGHT_AGENT_PROMPT = """You are a Flight Booking Agent. Your job is to help users book flights.
You need to collect all necessary information like:
- Origin city/airport
- Destination city/airport
- Date of travel
- Preferred time (morning, afternoon, evening)
- Number of passengers
- Class preference (economy, business, first)
- Any other preferences

Be conversational and helpful. Once you have all the required information, complete the booking 
and inform the user their flight has been booked successfully.

IMPORTANT: When you have completed the booking, end your response with: "BOOKING_COMPLETE"

Conversation history:
{conversation_history}

User: {user_input}
Flight Agent:"""

# --- LangGraph-compatible Flight Agent function ---
# def flight_agent(state: Dict[str, Any]) -> Dict[str, Any]:
#     state_obj = ConversationState.from_dict(state)
#     user_input = state.get("user_input", "")

#     prompt = ChatPromptTemplate.from_template(FLIGHT_AGENT_PROMPT)

#     messages = [
#         SystemMessage(content="You are a helpful Flight Booking Agent assistant."),
#         HumanMessage(content=prompt.format(
#             conversation_history=state_obj.get_conversation_history(),
#             user_input=user_input
#         ))
#     ]

#     response = flight_llm.invoke(messages)

#     state_obj.add_message("user", user_input)
#     agent_response = response.content
#     state_obj.add_message("assistant", agent_response)

#     if "BOOKING_COMPLETE" in agent_response:
#         clean_response = agent_response.replace("BOOKING_COMPLETE", "").strip()
#         state_obj.add_message("assistant", clean_response)
#         state_obj.booking_info["flight"]["status"] = "booked"
#         state_obj.booking_info["flight"]["details"] = "Flight booked based on user preferences"
#         state_obj.current_agent = AgentState.END

#     result = state_obj.to_dict()
#     result["user_input"] = ""  # Clear input for next round
#     return result

def flight_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    state_obj = ConversationState.from_dict(state)
    user_input = state.get("user_input", "")

    prompt = ChatPromptTemplate.from_template(FLIGHT_AGENT_PROMPT)

    messages = [
        SystemMessage(content="You are a helpful Flight Booking Agent assistant."),
        HumanMessage(content=prompt.format(
            conversation_history=state_obj.get_conversation_history(),
            user_input=user_input
        ))
    ]

    response = flight_llm.invoke(messages)

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
        state_obj.booking_info["flight"]["status"] = "booked"
        state_obj.booking_info["flight"]["details"] = "Flight booked based on user preferences"
        state_obj.current_agent = AgentState.END
    else:
        # Add the response as-is if booking is not complete
        state_obj.add_message("assistant", agent_response)

    result = state_obj.to_dict()
    result["user_input"] = ""  # Clear input for next round
    return result