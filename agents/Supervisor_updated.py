import os
from enum import Enum
from typing import Dict, Any, List

from flight_agent import flight_agent
from cab_agent import cab_agent

# --- Shared Agent State Enum ---
class AgentState(str, Enum):
    FLIGHT_AGENT = "flight_agent"
    CAB_AGENT = "cab_agent"
    END = "end"

def supervisor(state: Dict[str, Any]) -> Dict[str, Any]:
    current_agent = state.get("current_agent", AgentState.FLIGHT_AGENT)

    if current_agent == AgentState.FLIGHT_AGENT:
        state = flight_agent(state)
        if state["booking_info"].get("flight", {}).get("status") == "booked":
            print("\nSupervisor: Your flight is booked! Would you like to book a cab to the airport?")
            follow_up = input("You: ").lower()
            if "yes" in follow_up:
                state["current_agent"] = AgentState.CAB_AGENT
                # 👇 Call cab_agent immediately
                state = cab_agent(state)
            else:
                state["current_agent"] = AgentState.END

    elif current_agent == AgentState.CAB_AGENT:
        state = cab_agent(state)

    return state

def run_supervisor():
    state = {
        "messages": [],
        "current_agent": None,
        "booking_info": {
            "flight": {},
            "cab": {}
        },
        "user_input": ""
    }

    print("Welcome To Travel Booking Agent! Type 'stop' anytime to exit.")
    while True:
        # Exit if both bookings are complete
        if state["booking_info"]["flight"].get("status") == "booked" and \
           state["booking_info"]["cab"].get("status") == "booked":
            break

        # Only ask input if not already in the middle of an agent interaction
        if state["current_agent"] is None:
            user_input = input("You: ").strip().lower()
            if user_input == "stop":
                print("Supervisor: Stopping the booking process as requested.")
                break

            # Determine which agent to call
            if any(k in user_input for k in ["flight", "book a flight", "plane", "air ticket"]):
                state["current_agent"] = AgentState.FLIGHT_AGENT
            elif any(k in user_input for k in ["cab", "taxi", "ride", "airport drop"]):
                state["current_agent"] = AgentState.CAB_AGENT
            else:
                print("Supervisor: Sorry, I didn't understand. Do you want to book a flight or a cab?")
                continue

        # Get user input before agent call
        if state["current_agent"] is not None:
            user_input = input("You: ").strip()
            if user_input.lower() == "stop":
                print("Supervisor: Stopping the booking process as requested.")
                break
            state["user_input"] = user_input


        # Call the current agent
        state = supervisor(state)


        if state["messages"]:
            last_msg = state["messages"][-1]
            print(f"\n{last_msg['agent'].upper()} Agent: {last_msg['content']}\n")

        # Handle follow-up suggestions (same as before)
        if state["current_agent"] == AgentState.FLIGHT_AGENT and \
           state["booking_info"]["flight"].get("status") == "booked" and \
           state["booking_info"]["cab"].get("status") != "booked":
            print("Supervisor: Your flight is booked! Would you like to book a cab to the airport?")
            follow_up = input("You: ").lower()
            if follow_up == "stop":
                print("Supervisor: Stopping the booking process as requested.")
                break
            elif "yes" in follow_up:
                state["current_agent"] = AgentState.CAB_AGENT
                continue
            else:
                state["current_agent"] = None  # Reset to ask again later

        elif state["current_agent"] == AgentState.CAB_AGENT and \
             state["booking_info"]["cab"].get("status") == "booked" and \
             state["booking_info"]["flight"].get("status") != "booked":
            print("Supervisor: Your cab is booked! Would you like to book a flight as well?")
            follow_up = input("You: ").lower()
            if follow_up == "stop":
                print("Supervisor: Stopping the booking process as requested.")
                break
            elif "yes" in follow_up:
                state["current_agent"] = AgentState.FLIGHT_AGENT
                continue
            else:
                state["current_agent"] = None  # Reset to ask again later
        else:
            # If still in the middle of booking, continue with the same agent
            if not (
                state["booking_info"]["flight"].get("status") == "booked" and
                state["booking_info"]["cab"].get("status") == "booked"
            ):
                continue

    print("\nSupervisor: Thanks! Your booking process is complete.")


# --- If running standalone in Python ---
if __name__ == "__main__":
    run_supervisor()