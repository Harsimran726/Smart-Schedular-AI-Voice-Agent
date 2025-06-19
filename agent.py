import pandas as pd  
import numpy as np  
from langchain_core.prompts import ChatPromptTemplate
from langchain.agents import AgentExecutor, create_react_agent , BaseMultiActionAgent , initialize_agent, AgentType , create_openai_tools_agent , create_openai_functions_agent , create_tool_calling_agent
from langchain.tools import Tool
from langchain_google_genai import ChatGoogleGenerativeAI
import json
from langchain.memory import ConversationBufferMemory
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema.agent import AgentActionMessageLog
from langchain.agents.agent import AgentAction
from langchain.chains import LLMChain
from langchain_core.runnables import Runnable
import ast
import time 
# from __future__ import print_function
import datetime
import os.path
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

import os 
load_dotenv()
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')

# conversation like below:-
# user: Hi, I want to schedule the meeting
# bot: okay, let me know when you want and how much for
# user: let me know the schedule of monday or wednesday for 1 hour
# bot: yeah, I checked nad only 2 timing are avalible 5:30pm and 9 PM on both
# user: so , book the 5:30 PM Monday 
# bot: Thanks for schedule, your meeting is booked at 5:30 PM. 


# slot 
# slot = {
#     'date': "29th May",
#     'time': "5:00 PM",
#     'name': "Harsimran Singh",
#     'email': "harsimransing27448@gmail.com",
#     'desc': "Business Meeting"
# }



# Scope for full access to Google Calendar

def get_calendar_service():
    SCOPES = ['https://www.googleapis.com/auth/calendar']

    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)

    # If no (valid) token is available, login via OAuth flow
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)

        # Save token for future use
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    service = build('calendar', 'v3', credentials=creds)
    return service

# service = get_calendar_service()



def check_slots(details)-> None:
    print(f"inside check_slots")
    print(f"Type of details {type(details)}")
    print(f"details {details}")
    if type(details) is str:
        details = ast.literal_eval(details)
        print(f"Type of details {type(details)}")
    print(f"Here is details {details}")
    service = get_calendar_service()
    print(f"service {service}")
    calendar_id='primary'
    body = {
        "timeMin": details['start_time'],
        "timeMax": details['end_time'],
        "items": [{"id": calendar_id}]
    }
    print(f"Here in check_slots {body}")
    try:
        events_result = service.freebusy().query(body=body).execute()
        busy_times = events_result['calendars'][calendar_id]['busy']
        return busy_times
    except Exception as e:
        return f"Faield due to {e}"
    

def add_meet(details)-> None:
    details = ast.literal_eval(details)
    start_time = details['start_time']
    end_time = details['end_time']
    attendees = details['attendees'][0]
    service = get_calendar_service()
    print(f"here is detais in add_meet {details}")
    print(f"Here is attendees {attendees}")
    event = {
        'summary': details['summary'],
        'description': f"Meeting scheudled with",
        'start':{
            'dateTime':start_time,
            'timeZone':'Asia/Kolkata',
        },
        'end':{
            'dateTime': end_time,
            'timeZone':'Asia/Kolkata'
        },
        'attendees':[
            {'email':attendees}
        ]        
    }
    print(f"here is event in add_time {event}")
    event = service.events().insert(calendarId='primary',body=event,sendUpdates='all').execute()
    return f"Event successfully booked {event.get('htmlLink')}"

def stt():
    pass

def tts():
    pass

# def delete_slot(date_time:str,mail:str):
#     pass 


memory = ConversationBufferMemory(memory_key="chat_history",return_messages=True)

system_prompt = '''
    You are helpful Ai Assistant, help the user to Schedule a meeting with 'Harsimran Singh'. You working with more than 5+ Years of Experience. Following is your task you need to done professionally, step by step and with understanding :-
    - You ask to user when you want to schedule a meeting Day or Date with how much time meeting will goes it needs to ask time how much for meeting needed. 
    - If user tell about 20 Minutes then find 30 minutes slot from Harsimran Sing Calender or 35 minutes than 45 minutes. 
    - Provide them best 3 Timings, if timing are not available than you can provide alternative day to the user.
    - Collect the name, email, timing to the user if user tell only timing not name & mail then collect the mail and name don't book without these details.
    - After succesfully scheduled the meeting great the user with Thank message. 
    - You need to anlayse the date by your self here is current date and time.
    - After successfully booked the meet, great the user with Thanks message.

    Tools that you need to use during schedule the meeting:-
    - {{check_slots}} - Check the slots of the Harsimran Singh 
    - {{add_meet_calender}} - Schedule the meeting with Harsimran Singh after getting Name, mail and timing. 

    Data you need to pass between in Tools:-
    - {{check_slots}} -> use variable "details" (in dict) 'start_time','end_time'. 
                    ->> example:-
                    {{'start_time': '2025-06-22T17:00:00+05:30', 'end_time': '2025-06-22T17:30:00+05:30'}}
    - {{add_meet}} -> details (in dict) 'start_time','end_time','attendees'.
                   -> summary (str upto 50 words)
                   ->> Example - 
                   {{'start_time': '2025-06-22T17:00:00+05:30', 'end_time': '2025-06-22T17:30:00+05:30', 'attendees': ['harsimransd726@gmail.com'], 'summary': 'Meeting with Harsimran Singh'}}

    - if check_slots return empty then it means Harsimran is Avaliable. 
    Use this Date_Time Format:- '2025-06-17T14:00:00+05:30'
    

    
    '''



check_slots_calender = Tool(
    name="check_slots_available",
    description="Check the availability in Google Calender, pass the dictionary varialbe 'detials' containing 'start_time' and 'end_time' keys.",
    func=check_slots,
)

add_meet_calender = Tool(
    name="add_meeting_calender",
    description="Book or schedule the meeting with user.",
    func=add_meet,
)


llm = ChatGoogleGenerativeAI(model='gemini-2.5-flash-preview-05-20', 
    api_key=GOOGLE_API_KEY,
    temperature=0.8)


prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                system_prompt
            ),
             ("placeholder","{chat_history}"),
            ("human","{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ]
        )


Tools = [check_slots_calender,add_meet_calender]

agent = create_openai_functions_agent(llm=llm,tools=Tools,prompt=prompt)
conversation = AgentExecutor(agent=agent,tools=Tools,memory=memory,verbose=True)

def user_input(query: str):
    # query = input("Enter your message:-  ")
    date_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
    query = f"Current time:- {date_time}"  + f"user said: {query}"
    if query:
        try:
            response = conversation.invoke({"input":query})
            return response['output']
        except Exception as e:
            return f"SOrry please try again later {e}"
