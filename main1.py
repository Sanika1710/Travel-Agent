#The supervisor follow up questions are static/partially hardcoded

import streamlit as st
import os
from enum import Enum
from typing import Dict, Any, List
from datetime import datetime
import time

# Import your actual flight_agent and cab_agent modules
try:
    from agents.flight_agent import flight_agent
    from agents.cab_agent import cab_agent
    AGENTS_IMPORTED = True
except ImportError:
    AGENTS_IMPORTED = False
    st.error("⚠️ Could not import flight_agent and cab_agent modules. Please ensure they are in your Python path.")

# Wrapper functions to handle message format compatibility
def safe_flight_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """Wrapper for flight_agent with error handling and improved conversation flow"""
    if not AGENTS_IMPORTED:
        state["messages"].append({
            "agent": "flight",
            "content": "Flight agent module not available. Please check your imports.",
            "timestamp": datetime.now().isoformat()
        })
        return state
    
    try:
        # Check if flight booking is already complete by looking for explicit completion message
        if any(
            msg.get("agent") == "flight" and msg.get("content") == "BOOKING_COMPLETE"
            for msg in state.get("messages", [])
        ):
            return state
        
        agent_state = state.copy()
        
        formatted_messages = []
        system_context = None
        current_session_started = False
        
        # Process conversation history for flight agent
        for i, msg in enumerate(state.get("messages", [])):
            if (msg.get("agent") == "user" and 
                any(keyword in msg.get("content", "").lower() 
                    for keyword in ["book flight", "flight", "yes, book flight"])):
                current_session_started = True
                session_messages = state["messages"][i:]  # Start from the first relevant user input
                for session_msg in session_messages:
                    if isinstance(session_msg, dict):
                        if session_msg.get("agent") == "user":
                            formatted_messages.append({
                                "role": "user",
                                "content": session_msg.get("content", "")
                            })
                        elif session_msg.get("agent") == "flight":
                            formatted_messages.append({
                                "role": "assistant",
                                "content": session_msg.get("content", "")
                            })
                        elif session_msg.get("agent") == "supervisor":
                            # Capture supervisor message as system context
                            system_context = session_msg.get("content", "")
                break
        
        # If no session started, include the latest user input
        if not current_session_started and state.get("user_input"):
            formatted_messages.append({
                "role": "user",
                "content": state["user_input"]
            })
        
        # Add system context if it exists
        if system_context:
            formatted_messages.insert(0, {
                "role": "system",
                "content": system_context
            })
        
        agent_state["messages"] = formatted_messages
        
        # Call the actual flight agent
        result_state = flight_agent(agent_state)
        
        # Extract only NEW agent messages, skipping duplicates
        if "messages" in result_state:
            for msg in result_state["messages"]:
                if isinstance(msg, dict):
                    if msg.get("role") == "assistant" or msg.get("agent") == "flight":
                        content = msg.get("content", "")
                        if "BOOKING_COMPLETE" in content:
                            continue
                        is_duplicate = any(
                            existing_msg.get("content") == content and existing_msg.get("agent") == "flight"
                            for existing_msg in state["messages"]
                        )
                        
                        if not is_duplicate and content.strip():
                            state["messages"].append({
                                "agent": "flight",
                                "content": content,
                                "timestamp": datetime.now().isoformat()
                            })
        
        # Update booking info and check for completion with stricter conditions
        if (result_state["booking_info"]["flight"].get("status") == "booked" and 
            any(msg.get("role") == "assistant" and "your flight has been booked" in msg.get("content", "").lower() 
                for msg in result_state.get("messages", []))):
            state["booking_info"]["flight"] = result_state["booking_info"]["flight"]
            is_completion_message_already_added = any(
                msg.get("content") == "BOOKING_COMPLETE" and msg.get("agent") == "flight"
                for msg in state["messages"]
            )
            if not is_completion_message_already_added:
                state["messages"].append({
                    "agent": "flight",
                    "content": "BOOKING_COMPLETE",
                    "timestamp": datetime.now().isoformat()
                })
        
        return state
        
    except Exception as e:
        st.error(f"Error in flight_agent: {str(e)}")
        state["messages"].append({
            "agent": "flight",
            "content": f"Sorry, I encountered an error: {str(e)}. Please try again.",
            "timestamp": datetime.now().isoformat()
        })
        return state

def safe_cab_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    if not AGENTS_IMPORTED:
        state["messages"].append({
            "agent": "cab",
            "content": "Cab agent module not available. Please check your imports.",
            "timestamp": datetime.now().isoformat()
        })
        return state
    
    try:
        # Check if cab booking is already complete by looking for explicit completion message
        if any(
            msg.get("agent") == "cab" and msg.get("content") == "BOOKING_COMPLETE"
            for msg in state.get("messages", [])
        ):
            return state
        
        agent_state = state.copy()
        
        formatted_messages = []
        system_context = None
        current_session_started = False
        
        # Process conversation history for cab agent
        for i, msg in enumerate(state.get("messages", [])):
            if (msg.get("agent") == "user" and 
                any(keyword in msg.get("content", "").lower() 
                    for keyword in ["book cab", "cab", "taxi", "yes, book cab"])):
                current_session_started = True
                session_messages = state["messages"][i:]
                for session_msg in session_messages:
                    if isinstance(session_msg, dict):
                        if session_msg.get("agent") == "user":
                            formatted_messages.append({
                                "role": "user",
                                "content": session_msg.get("content", "")
                            })
                        elif session_msg.get("agent") == "cab":
                            formatted_messages.append({
                                "role": "assistant",
                                "content": session_msg.get("content", "")
                            })
                        elif session_msg.get("agent") == "supervisor":
                            system_context = session_msg.get("content", "")
                break
        
        if not current_session_started and state.get("user_input"):
            formatted_messages.append({
                "role": "user",
                "content": state["user_input"]
            })
        
        if system_context:
            formatted_messages.insert(0, {
                "role": "system",
                "content": system_context
            })
        
        agent_state["messages"] = formatted_messages
        
        # Call the actual cab agent
        result_state = cab_agent(agent_state)
        
        # Extract only NEW agent messages, skipping duplicates
        if "messages" in result_state:
            for msg in result_state["messages"]:
                if isinstance(msg, dict):
                    if msg.get("role") == "assistant" or msg.get("agent") == "cab":
                        content = msg.get("content", "")
                        if "BOOKING_COMPLETE" in content:
                            continue
                        is_duplicate = any(
                            existing_msg.get("content") == content and existing_msg.get("agent") == "cab"
                            for existing_msg in state["messages"]
                        )
                        
                        if not is_duplicate and content.strip():
                            state["messages"].append({
                                "agent": "cab",
                                "content": content,
                                "timestamp": datetime.now().isoformat()
                            })
        
        # Update booking info and check for confirmation before marking as complete
        if "cab" in result_state["booking_info"]:
            # Check if the cab agent is waiting for confirmation
            if (result_state["booking_info"]["cab"].get("status") == "pending_confirmation" and 
                any(msg.get("role") == "assistant" and "to confirm" in msg.get("content", "").lower() 
                    for msg in result_state.get("messages", []))):
                state["booking_info"]["cab"] = result_state["booking_info"]["cab"]
                # Wait for user confirmation (e.g., "Yes, book it" or "No, I have special requests")
                last_user_input = state.get("user_input", "").lower()
                if "yes" in last_user_input or "book it" in last_user_input:
                    state["booking_info"]["cab"]["status"] = "booked"
                    state["messages"].append({
                        "agent": "cab",
                        "content": "Your cab has been booked successfully!",
                        "timestamp": datetime.now().isoformat()
                    })
                    state["messages"].append({
                        "agent": "cab",
                        "content": "BOOKING_COMPLETE",
                        "timestamp": datetime.now().isoformat()
                    })
                elif "no" in last_user_input or "special request" in last_user_input:
                    state["booking_info"]["cab"]["status"] = "awaiting_special_requests"
                    state["messages"].append({
                        "agent": "cab",
                        "content": "Please provide your special requests, and I'll update the booking accordingly.",
                        "timestamp": datetime.now().isoformat()
                    })
            elif (result_state["booking_info"]["cab"].get("status") == "booked" and 
                  any(msg.get("role") == "assistant" and "your cab has been booked" in msg.get("content", "").lower() 
                      for msg in result_state.get("messages", []))):
                state["booking_info"]["cab"] = result_state["booking_info"]["cab"]
                is_completion_message_already_added = any(
                    msg.get("content") == "BOOKING_COMPLETE" and msg.get("agent") == "cab"
                    for msg in state["messages"]
                )
                if not is_completion_message_already_added:
                    state["messages"].append({
                        "agent": "cab",
                        "content": "BOOKING_COMPLETE",
                        "timestamp": datetime.now().isoformat()
                    })
        
        return state
        
    except Exception as e:
        st.error(f"Error in cab_agent: {str(e)}")
        state["messages"].append({
            "agent": "cab",
            "content": f"Sorry, I encountered an error: {str(e)}. Please try again.",
            "timestamp": datetime.now().isoformat()
        })
        return state

# --- Shared Agent State Enum ---
class AgentState(str, Enum):
    FLIGHT_AGENT = "flight_agent"
    CAB_AGENT = "cab_agent"
    END = "end"

def supervisor(state: Dict[str, Any]) -> Dict[str, Any]:
    """Supervisor function to route tasks to appropriate agents and share context"""
    current_agent = state.get("current_agent")
    
    # If we're switching agents, clear any previous agent-specific state
    if current_agent == AgentState.FLIGHT_AGENT:
        if "cab_context" in state:
            del state["cab_context"]
        
        # Check if the user has confirmed the follow-up question
        user_confirmed = any(
            msg.get("agent") == "user" and msg.get("content", "").lower() == "yes, book flight"
            for msg in state.get("messages", [])
        )
        
        # Only pass context if user has confirmed the follow-up
        flight_messages_exist = any(msg.get("agent") == "flight" for msg in state.get("messages", []))
        if not flight_messages_exist and user_confirmed:
            # Find the last cab agent message before BOOKING_COMPLETE
            cab_summary = None
            for msg in reversed(state.get("messages", [])):
                if msg.get("agent") == "cab" and msg.get("content") != "BOOKING_COMPLETE":
                    cab_summary = msg.get("content")
                    break
            
            if cab_summary:
                # Craft a message for the flight agent with the cab summary and user input
                last_user_input = state.get("user_input", "book flight")
                supervisor_message = (
                    f"The user wants to book a flight: '{last_user_input}'. They have just completed a cab booking. Here are the details:\n\n"
                    f"{cab_summary}\n\n"
                    f"Please assist the user in booking a flight based on this cab information. "
                    f"For example, suggest a flight that aligns with the cab's pickup or drop-off location and time."
                )
                state["messages"].append({
                    "agent": "supervisor",
                    "content": supervisor_message,
                    "timestamp": datetime.now().isoformat()
                })
            else:
                # Fallback if no cab summary is found
                supervisor_message = (
                    f"The user wants to book a flight: '{last_user_input}'. I don't have prior cab booking details. "
                    f"Please assist them with the booking process by asking for their origin, destination, and preferred travel date and time."
                )
                state["messages"].append({
                    "agent": "supervisor",
                    "content": supervisor_message,
                    "timestamp": datetime.now().isoformat()
                })
        
        state = safe_flight_agent(state)
        
    elif current_agent == AgentState.CAB_AGENT:
        if "flight_context" in state:
            del state["flight_context"]
        
        # Check if the user has confirmed the follow-up question
        user_confirmed = any(
            msg.get("agent") == "user" and msg.get("content", "").lower() == "yes, book cab"
            for msg in state.get("messages", [])
        )
        
        # Only pass context if user has confirmed the follow-up
        cab_messages_exist = any(msg.get("agent") == "cab" for msg in state.get("messages", []))
        if not cab_messages_exist and user_confirmed:
            # Find the last flight agent message before BOOKING_COMPLETE
            flight_summary = None
            for msg in reversed(state.get("messages", [])):
                if msg.get("agent") == "flight" and msg.get("content") != "BOOKING_COMPLETE":
                    flight_summary = msg.get("content")
                    break
            
            if flight_summary:
                # Craft a message for the cab agent with the flight summary and user input
                last_user_input = state.get("user_input", "book cab")
                supervisor_message = (
                    f"The user wants to book a cab: '{last_user_input}'. They have just completed a flight booking. Here are the details:\n\n"
                    f"{flight_summary}\n\n"
                    f"Please assist the user in booking a cab based on this flight information. "
                    f"For example, suggest a cab to the departure airport a few hours before the flight, "
                    f"or a cab from the 'arrival airport' after landing "
                    f"or BOTH"
                )
                state["messages"].append({
                    "agent": "supervisor",
                    "content": supervisor_message,
                    "timestamp": datetime.now().isoformat()
                })
            else:
                # Fallback if no flight summary is found
                supervisor_message = (
                    f"The user wants to book a cab: '{last_user_input}'. I don't have prior flight booking details. "
                    f"Please assist them with the booking process by asking for their pickup location, destination, and preferred time."
                )
                state["messages"].append({
                    "agent": "supervisor",
                    "content": supervisor_message,
                    "timestamp": datetime.now().isoformat()
                })
        
        state = safe_cab_agent(state)
    else:
        # Handle initial case
        if not state.get("messages") or state["messages"][-1]["agent"] != "supervisor":
            state["messages"].append({
                "agent": "supervisor",
                "content": "I can help you book flights and cabs. Would you like to book a flight or a cab?",
                "timestamp": datetime.now().isoformat()
            })
    
    return state

# --- Streamlit Configuration ---
st.set_page_config(
    page_title="Travel Booking Agent",
    page_icon="🧳",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Initialize Session State ---
def initialize_session_state():
    if "state" not in st.session_state:
        st.session_state.state = {
            "messages": [],
            "current_agent": None,
            "booking_info": {
                "flight": {},
                "cab": {}
            },
            "user_input": "",
            "conversation_stage": "initial"  # initial, flight_booking, cab_booking, completed
        }
    if "show_follow_up" not in st.session_state:
        st.session_state.show_follow_up = False
    if "follow_up_type" not in st.session_state:
        st.session_state.follow_up_type = None
    if "follow_up_declined" not in st.session_state:
        st.session_state.follow_up_declined = False

# --- Custom CSS ---
def load_css():
    st.markdown("""
    <style>
    .main-header {
        text-align: center;
        padding: 1.5rem 0;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 15px;
        margin-bottom: 2rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    .user-message {
        background-color: #e3f2fd;
        color: #000;
        padding: 1rem;
        border-radius: 15px;
        margin: 0.5rem 0;
        border-left: 4px solid #2196f3;
    }
    
    .supervisor-message {
        background-color: #fff3e0;
        color: #000;
        padding: 1rem;
        border-radius: 15px;
        margin: 0.5rem 0;
        border-left: 4px solid #ff9800;
    }
    
    .flight-agent-message {
        background-color: #f3e5f5;
        color: #000;
        padding: 1rem;
        border-radius: 15px;
        margin: 0.5rem 0;
        border-left: 4px solid #9c27b0;
    }
    
    .cab-agent-message {
        background-color: #e8f5e8;
        color: #000;
        padding: 1rem;
        border-radius: 15px;
        margin: 0.5rem 0;
        border-left: 4px solid #4caf50;
    }
    
    .booking-status {
        background-color: #f5f5f5;
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        border: 2px solid #ddd;
    }
    
    .booking-complete {
        background-color: #e8f5e8;
        padding: 1.5rem;
        border-radius: 15px;
        border: 2px solid #4caf50;
        text-align: center;
        color: #2e7d32;
        font-weight: bold;
        animation: pulse 2s infinite;
    }
    
    .follow-up-section {
        background-color: #fff8e1;
        color: #000;
        padding: 1rem;
        border-radius: 10px;
        border-left: 4px solid #ffc107;
        margin: 1rem 0;
    }
    
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    @keyframes pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.02); }
        100% { transform: scale(1); }
    }
    
    .status-card {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin: 0.5rem 0;
    }
    </style>
    """, unsafe_allow_html=True)

# --- Helper Functions ---
def display_booking_status():
    """Display current booking status in sidebar without details"""
    flight_status = st.session_state.state["booking_info"]["flight"]
    cab_status = st.session_state.state["booking_info"]["cab"]
    
    st.sidebar.subheader("📊 Booking Status")
    
    # Flight Status
    if flight_status.get("status") == "booked":
        st.sidebar.success("✈️ Flight: Booked")
    else:
        st.sidebar.info("✈️ Flight: Not booked")
    
    # Cab Status
    if cab_status.get("status") == "booked":
        st.sidebar.success("🚗 Cab: Booked")
    else:
        st.sidebar.info("🚗 Cab: Not booked")

def get_agent_icon(agent_type):
    """Get icon for different agent types"""
    icons = {
        "supervisor": "🎯",
        "flight": "✈️",
        "cab": "🚗",
        "user": "👤"
    }
    return icons.get(agent_type, "🤖")

def check_completion_status():
    """Check if both bookings are complete"""
    flight_booked = st.session_state.state["booking_info"]["flight"].get("status") == "booked"
    cab_booked = st.session_state.state["booking_info"]["cab"].get("status") == "booked"
    return flight_booked and cab_booked

def should_show_follow_up():
    """Determine if follow-up question should be shown"""
    # If the user has already declined the follow-up, don't show it again
    if st.session_state.follow_up_declined:
        return None
    
    flight_booked = st.session_state.state["booking_info"]["flight"].get("status") == "booked"
    cab_booked = st.session_state.state["booking_info"]["cab"].get("status") == "booked"
    current_agent = st.session_state.state["current_agent"]
    
    # If an agent is already active, don't show the follow-up question
    if current_agent in [AgentState.FLIGHT_AGENT, AgentState.CAB_AGENT]:
        return None
    
    if flight_booked and not cab_booked and not st.session_state.show_follow_up:
        return "cab"
    elif cab_booked and not flight_booked and not st.session_state.show_follow_up:
        return "flight"
    return None

def preserve_scroll_position():
    scroll_script = """
    <script>
        window.addEventListener('load', function() {
            const chatContainer = document.getElementById('chat-container');
            if (chatContainer) {
                chatContainer.scrollIntoView({ behavior: 'smooth' });
            }
        });
    </script>
    """
    st.markdown(scroll_script, unsafe_allow_html=True)

# --- Main App ---
def main():
    load_css()
    initialize_session_state()
    preserve_scroll_position()
    
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>🧳 Travel Booking Agent</h1>
        <p>Your AI-Powered Travel Assistant - Book Flights & Cabs Seamlessly</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.header("🎯 Supervisor Dashboard")
        display_booking_status()
        
        st.markdown("---")
        st.write("**Available Services:**")
        st.write("• ✈️ Flight Booking")
        st.write("• 🚗 Cab/Taxi Booking")
        st.write("• 🎯 Smart Recommendations")
        
        st.markdown("---")
        if st.button("🔄 Start New Booking", type="secondary"):
            st.session_state.state = {
                "messages": [],
                "current_agent": None,
                "booking_info": {"flight": {}, "cab": {}},
                "user_input": "",
                "conversation_stage": "initial"
            }
            st.session_state.show_follow_up = False
            st.session_state.follow_up_type = None
            st.session_state.follow_up_declined = False
            st.rerun()
    
    # Main chat interface
    # st.subheader("💬 Conversation with Travel Agents")
    st.markdown('<div id="chat-container"></div>', unsafe_allow_html=True)
    
    # Display conversation history
    chat_container = st.container()
    
    with chat_container:
        if not st.session_state.state["messages"]:
            st.markdown("""
            <div class="supervisor-message">
                <strong>🎯 Supervisor:</strong><br>
                Welcome to Travel Booking Agent! I can help you book flights and cabs. 
                What would you like to book today?
            </div>
            """, unsafe_allow_html=True)
        
        for message in st.session_state.state["messages"]:
            agent_type = message.get("agent", "supervisor")
            icon = get_agent_icon(agent_type)
            agent_name = agent_type.replace("_", " ").title()
            
            css_class = f"{agent_type.replace('_', '-')}-message"
            
            st.markdown(f"""
            <div class="{css_class}">
                <strong>{icon} {agent_name} Agent:</strong><br>
                {message["content"]}
            </div>
            """, unsafe_allow_html=True)
    
    # Check for follow-up questions
    follow_up_needed = should_show_follow_up()
    if follow_up_needed and not st.session_state.show_follow_up:
        st.session_state.show_follow_up = True
        st.session_state.follow_up_type = follow_up_needed
    
    # Display follow-up question
    if st.session_state.show_follow_up and not check_completion_status():
        service_name = "cab" if st.session_state.follow_up_type == "cab" else "flight"
        other_service = "flight" if service_name == "cab" else "cab"
        
        # Reuse the supervisor's logic to get the last agent message for context
        booking_summary = None
        for msg in reversed(st.session_state.state.get("messages", [])):
            if msg.get("agent") == other_service and msg.get("content") != "BOOKING_COMPLETE":
                content = msg.get("content")
                if "from" in content:
                    booking_summary = content[content.lower().find("from"):]  # Extract from "from" onwards
                else:
                    booking_summary = content  # fallback to full content
                break

        # Construct dynamic follow-up message
        if booking_summary:
            follow_up_message = (
                f"You have successfully booked your {other_service} {booking_summary}. "
                f"Would you like to book a {service_name} as well to complement your trip?"
            )
        else:
            follow_up_message = (
                f"You have successfully booked your {other_service}. "
                f"Would you like to book a {service_name} as well to complement your trip?"
            )

        
        st.markdown(f"""
        <div class="follow-up-section">
            <strong>🎯 Supervisor:</strong><br>
            {follow_up_message}
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            if st.button(f"✅ Yes, book {service_name}", key="yes_follow_up"):
                # Clear any previous booking context for the new service
                if service_name == "flight":
                    st.session_state.state["booking_info"]["flight"] = {}
                else:
                    st.session_state.state["booking_info"]["cab"] = {}
                
                # Clear any agent-specific context that might persist
                st.session_state.state.pop("flight_context", None)
                st.session_state.state.pop("cab_context", None)
                
                # Add messages to conversation
                st.session_state.state["messages"].append({
                    "agent": "supervisor",
                    "content": follow_up_message,
                    "timestamp": datetime.now().isoformat()
                })
                
                st.session_state.state["messages"].append({
                    "agent": "user",
                    "content": f"Yes, book {service_name}",
                    "timestamp": datetime.now().isoformat()
                })
                
                # Set the appropriate agent and reset conversation stage
                st.session_state.state["current_agent"] = AgentState.CAB_AGENT if service_name == "cab" else AgentState.FLIGHT_AGENT
                st.session_state.state["user_input"] = f"book {service_name}"
                st.session_state.state["conversation_stage"] = f"{service_name}_booking"
                
                st.session_state.show_follow_up = False
                st.session_state.follow_up_type = None
                
                # Process through supervisor to initialize the new agent
                with st.spinner(f"Connecting you to the {service_name} agent..."):
                    st.session_state.state = supervisor(st.session_state.state)
                
                st.rerun()

        with col2:
            if st.button("❌ No, thanks", key="no_follow_up"):
                # Add supervisor message to conversation
                st.session_state.state["messages"].append({
                    "agent": "supervisor",
                    "content": follow_up_message,
                    "timestamp": datetime.now().isoformat()
                })
                
                # Add user response to conversation
                st.session_state.state["messages"].append({
                    "agent": "user",
                    "content": "No, thanks",
                    "timestamp": datetime.now().isoformat()
                })
                
                # Add supervisor response
                st.session_state.state["messages"].append({
                    "agent": "supervisor",
                    "content": "Thank you for using our travel booking service! Have a great trip!",
                    "timestamp": datetime.now().isoformat()
                })
                
                st.session_state.show_follow_up = False
                st.session_state.follow_up_type = None
                st.session_state.follow_up_declined = True
                st.session_state.state["conversation_stage"] = "completed"
                st.rerun()
        
        # Check if both bookings are complete
        if check_completion_status():
            st.markdown("""
            <div class="booking-complete">
                🎉 Congratulations! Your travel booking is complete! 🎉<br>
                Both your flight and cab have been successfully booked.
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("🆕 Start New Booking", type="primary"):
                st.session_state.state = {
                    "messages": [],
                    "current_agent": None,
                    "booking_info": {"flight": {}, "cab": {}},
                    "user_input": "",
                    "conversation_stage": "initial"
                }
                st.session_state.show_follow_up = False
                st.session_state.follow_up_type = None
                st.session_state.follow_up_declined = False
                st.rerun()

    # Chat input with kill switch
    if not check_completion_status() and (
        not st.session_state.show_follow_up or 
        st.session_state.state["current_agent"] in [AgentState.FLIGHT_AGENT, AgentState.CAB_AGENT]
    ):
        user_input = st.chat_input("Please provide the details (e.g., pickup location, flight destination, etc.)")
        
        if user_input:
            # Add user message to history
            st.session_state.state["messages"].append({
                "agent": "user",
                "content": user_input,
                "timestamp": datetime.now().isoformat()
            })
            
            # Check for kill switch
            user_input_lower = user_input.lower()
            if "stop" in user_input_lower:
                st.session_state.state["messages"].append({
                    "agent": "supervisor",
                    "content": "Booking process stopped. How can I assist you further?",
                    "timestamp": datetime.now().isoformat()
                })
                st.session_state.state["current_agent"] = None
                st.session_state.state["conversation_stage"] = "initial"
                st.rerun()
            else:
                # Determine which agent to activate first
                if st.session_state.state["current_agent"] is None:
                    if any(k in user_input_lower for k in ["flight", "book a flight", "plane", "air ticket", "fly"]):
                        st.session_state.state["current_agent"] = AgentState.FLIGHT_AGENT
                        st.session_state.state["conversation_stage"] = "flight_booking"
                    elif any(k in user_input_lower for k in ["cab", "taxi", "ride", "airport drop", "uber", "lyft"]):
                        st.session_state.state["current_agent"] = AgentState.CAB_AGENT
                        st.session_state.state["conversation_stage"] = "cab_booking"
                    else:
                        # Supervisor handles unclear requests
                        st.session_state.state["messages"].append({
                            "agent": "supervisor",
                            "content": "I can help you book flights and cabs! Please specify if you'd like to book a flight or a cab/taxi.",
                            "timestamp": datetime.now().isoformat()
                        })
                        st.rerun()
                        return
                
                # Set user input and process through supervisor
                st.session_state.state["user_input"] = user_input
                with st.spinner("Processing your request..."):
                    st.session_state.state = supervisor(st.session_state.state)
                
                # Reset current agent only if booking is fully complete
                if st.session_state.state["current_agent"] is not None:
                    current_booking_type = "flight" if st.session_state.state["current_agent"] == AgentState.FLIGHT_AGENT else "cab"
                    if st.session_state.state["booking_info"][current_booking_type].get("status") == "booked":
                        st.session_state.state["current_agent"] = None
                        st.session_state.state["conversation_stage"] = "completed"
                        st.session_state.show_follow_up = False
                
                st.rerun()

if __name__ == "__main__":
    main()