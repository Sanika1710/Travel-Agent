# agents/supervisor_agent.py
import os
from typing import List, Dict, Any, Optional
from enum import Enum
from datetime import datetime
import json

from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage

# --- Model setup ---
os.environ["GROQ_API_KEY"] = "API_KEY"  # Replace with secure method in prod
MODEL = "llama3-70b-8192"
supervisor_llm = ChatGroq(temperature=0.3, model_name=MODEL)

# --- Agent states ---
class AgentState(str, Enum):
    SUPERVISOR = "supervisor"
    FLIGHT_AGENT = "flight_agent"
    CAB_AGENT = "cab_agent"
    END = "end"

# --- Conversation state management ---
class SupervisorState:
    def __init__(self):
        self.messages: List[Dict[str, Any]] = []
        self.current_agent: Optional[AgentState] = None
        self.booking_info: Dict[str, Any] = {
            "flight": {},
            "cab": {}
        }

    def add_message(self, role: str, content: str, agent: Optional[AgentState] = None):
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "agent": agent if agent else AgentState.SUPERVISOR
        })

    def get_conversation_history(self) -> str:
        history = ""
        for msg in self.messages[-5:]:  # Limit to last 5 messages for context
            agent_prefix = f"[{msg.get('agent', msg.get('role', 'unknown'))}] "
            content = msg.get('content', 'No content')
            role = msg.get('role', msg.get('agent', 'unknown'))
            history += f"{agent_prefix}{role}: {content}\n\n"
        return history

    def to_dict(self) -> Dict[str, Any]:
        return {
            "messages": self.messages,
            "current_agent": self.current_agent,
            "booking_info": self.booking_info,
            "user_input": ""
        }

    @classmethod
    def from_dict(cls, state_dict: Dict[str, Any]) -> 'SupervisorState':
        state = cls()
        state.messages = state_dict.get("messages", [])
        state.current_agent = state_dict.get("current_agent")
        state.booking_info = state_dict.get("booking_info", {"flight": {}, "cab": {}})
        return state

# --- Prompt template for Supervisor Agent ---
SUPERVISOR_PROMPT = """You are a Supervisor Agent for a travel booking system. Your role is to:
1. Analyze the user's input and booking status to determine whether to route to the flight agent, cab agent, or ask for clarification.
2. If a flight or cab booking is complete, suggest the complementary service (e.g., cab after flight, flight after cab) using the booking details.
3. Provide context to the next agent based on existing bookings.
4. Keep the tone friendly, professional, and concise. Do NOT repeat the user's input verbatim in your response.

Booking status:
- Flight: {flight_status}
- Cab: {cab_status}

Booking details:
{booking_details}

Conversation history (last 5 messages):
{conversation_history}

User input: {user_input}

Instructions:
- If the user specifies "flight" or related keywords (e.g., "book a flight", "plane", "fly"), route to the flight agent with a concise message like "Routing you to the flight agent to book your flight."
- If the user specifies "cab" or related keywords (e.g., "book a cab", "taxi", "ride"), route to the cab agent with a concise message like "Routing you to the cab agent to book your cab."
- If a flight is booked but no cab is booked, you MUST suggest booking a cab based on flight details. Use a message like "Your flight is booked. Would you like to book a cab to the departure airport or from the arrival airport to complete your travel plans?"
- If a cab is booked but no flight is booked, you MUST suggest booking a flight that aligns with the cab's schedule (e.g., "Your cab is booked. Would you like to book a flight that aligns with your cab schedule?").
- If the input is unclear, ask for clarification (e.g., "Would you like to book a flight or a cab?").
- If the user says "stop", end the current booking process and ask how to assist further.
- If both flight and cab are booked, confirm completion and ask if the user wants to start a new booking.
- Do NOT repeat the user's input in your response. Summarize or rephrase it if needed for context.

Supervisor Response:"""

def supervisor_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    state_obj = SupervisorState.from_dict(state)
    user_input = state.get("user_input", "").lower()

    # Prepare booking status and details
    flight_booked = state_obj.booking_info["flight"].get("status") == "booked"
    cab_booked = state_obj.booking_info["cab"].get("status") == "booked"
    flight_status = "booked" if flight_booked else "not booked"
    cab_status = "booked" if cab_booked else "not booked"
    booking_details = json.dumps(state_obj.booking_info, indent=2)

    # Create prompt
    prompt = ChatPromptTemplate.from_template(SUPERVISOR_PROMPT)
    messages = [
        SystemMessage(content="You are a helpful Supervisor Agent for a travel booking system."),
        HumanMessage(content=prompt.format(
            flight_status=flight_status,
            cab_status=cab_status,
            booking_details=booking_details,
            conversation_history=state_obj.get_conversation_history(),
            user_input=user_input
        ))
    ]

    # Call LLM
    try:
        response = supervisor_llm.invoke(messages)
        supervisor_response = response.content.strip()
    except Exception as e:
        supervisor_response = f"Error processing request: {str(e)}. Please try again."

    # Always add the supervisor response as a new message
    state_obj.add_message("assistant", supervisor_response, agent=AgentState.SUPERVISOR)

    # Determine next steps with fallback logic
    if "stop" in user_input:
        state_obj.current_agent = None
        state_obj.add_message("assistant", "Booking process stopped. How can I assist you further?", agent=AgentState.SUPERVISOR)
    elif flight_booked and not cab_booked and state_obj.current_agent != AgentState.CAB_AGENT:
        # Ensure cab suggestion if not already in the response
        if "cab" not in supervisor_response.lower():
            supervisor_response = f"Your flight from {state_obj.booking_info['flight'].get('origin', 'your departure city')} to {state_obj.booking_info['flight'].get('destination', 'your destination')} on {state_obj.booking_info['flight'].get('date', 'your travel date')} at {state_obj.booking_info['flight'].get('time', 'your travel time')} is booked. Would you like to book a cab to the departure airport or from the arrival airport to complete your travel plans?"
            state_obj.add_message("assistant", supervisor_response, agent=AgentState.SUPERVISOR)
        state_obj.current_agent = None
    elif cab_booked and not flight_booked and state_obj.current_agent != AgentState.FLIGHT_AGENT:
        # Ensure flight suggestion
        if "flight" not in supervisor_response.lower():
            supervisor_response = f"Your cab from {state_obj.booking_info['cab'].get('pickup_location', 'your pickup location')} at {state_obj.booking_info['cab'].get('pickup_time', 'your pickup time')} is booked. Would you like to book a flight that aligns with your cab schedule?"
            state_obj.add_message("assistant", supervisor_response, agent=AgentState.SUPERVISOR)
        state_obj.current_agent = None
    elif any(k in user_input for k in ["flight", "book a flight", "plane", "air ticket", "fly"]):
        state_obj.current_agent = AgentState.FLIGHT_AGENT
    elif any(k in user_input for k in ["cab", "taxi", "ride", "airport drop", "uber", "lyft"]):
        state_obj.current_agent = AgentState.CAB_AGENT
    elif (flight_booked and cab_booked and 
          state_obj.current_agent not in [AgentState.FLIGHT_AGENT, AgentState.CAB_AGENT]):
        state_obj.current_agent = AgentState.END
        state_obj.add_message("assistant", "Both flight and cab bookings are complete! Would you like to start a new booking?", agent=AgentState.SUPERVISOR)

    result = state_obj.to_dict()
    result["user_input"] = ""  # Clear input for next step
    return result

# def supervisor_agent(state: Dict[str, Any]) -> Dict[str, Any]:
#     state_obj = SupervisorState.from_dict(state)
#     user_input = state.get("user_input", "").lower()

#     # Prepare booking status and details
#     flight_booked = state_obj.booking_info["flight"].get("status") == "booked"
#     cab_booked = state_obj.booking_info["cab"].get("status") == "booked"
#     flight_status = "booked" if flight_booked else "not booked"
#     cab_status = "booked" if cab_booked else "not booked"
#     booking_details = json.dumps(state_obj.booking_info, indent=2)

#     # Create prompt
#     prompt = ChatPromptTemplate.from_template(SUPERVISOR_PROMPT)
#     messages = [
#         SystemMessage(content="You are a helpful Supervisor Agent for a travel booking system."),
#         HumanMessage(content=prompt.format(
#             flight_status=flight_status,
#             cab_status=cab_status,
#             booking_details=booking_details,
#             conversation_history=state_obj.get_conversation_history(),
#             user_input=user_input
#         ))
#     ]

#     # Call LLM
#     try:
#         response = supervisor_llm.invoke(messages)
#         supervisor_response = response.content.strip()
#     except Exception as e:
#         supervisor_response = f"Error processing request: {str(e)}. Please try again."

#     # Always add the supervisor response as a new message
#     state_obj.add_message("assistant", supervisor_response, agent=AgentState.SUPERVISOR.value)

#     # Determine next steps with fallback logic
#     if "stop" in user_input:
#         state_obj.current_agent = None
#         state_obj.add_message("assistant", "Booking process stopped. How can I assist you further?", agent=AgentState.SUPERVISOR.value)
#     elif flight_booked and not cab_booked and state_obj.current_agent != AgentState.CAB_AGENT.value:
#         # Ensure cab suggestion if not already in the response
#         if "cab" not in supervisor_response.lower():
#             supervisor_response = f"Your flight from {state_obj.booking_info['flight'].get('origin', 'your departure city')} to {state_obj.booking_info['flight'].get('destination', 'your destination')} on {state_obj.booking_info['flight'].get('date', 'your travel date')} at {state_obj.booking_info['flight'].get('time', 'your travel time')} is booked. Would you like to book a cab to the departure airport or from the arrival airport to complete your travel plans?"
#             state_obj.add_message("assistant", supervisor_response, agent=AgentState.SUPERVISOR.value)
#         state_obj.current_agent = None
#     elif cab_booked and not flight_booked and state_obj.current_agent != AgentState.FLIGHT_AGENT.value:
#         # Ensure flight suggestion
#         if "flight" not in supervisor_response.lower():
#             supervisor_response = f"Your cab from {state_obj.booking_info['cab'].get('pickup_location', 'your pickup location')} at {state_obj.booking_info['cab'].get('pickup_time', 'your pickup time')} is booked. Would you like to book a flight that aligns with your cab schedule?"
#             state_obj.add_message("assistant", supervisor_response, agent=AgentState.SUPERVISOR.value)
#         state_obj.current_agent = None
#     elif any(k in user_input for k in ["flight", "book a flight", "plane", "air ticket", "fly"]):
#         state_obj.current_agent = AgentState.FLIGHT_AGENT.value
#     elif any(k in user_input for k in ["cab", "taxi", "ride", "airport drop", "uber", "lyft"]):
#         state_obj.current_agent = AgentState.CAB_AGENT.value
#     elif (flight_booked and cab_booked and 
#           state_obj.current_agent not in [AgentState.FLIGHT_AGENT.value, AgentState.CAB_AGENT.value]):
#         state_obj.current_agent = AgentState.END.value
#         state_obj.add_message("assistant", "Both flight and cab bookings are complete! Would you like to start a new booking?", agent=AgentState.SUPERVISOR.value)

#     result = state_obj.to_dict()
#     result["user_input"] = ""  # Clear input for next step
#     return result