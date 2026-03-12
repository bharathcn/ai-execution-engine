import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate_plan(goal_text):
    prompt = f"""User goal: {goal_text}
Create a 7 day execution plan.
Return ONLY valid JSON in this format:

{{
 "plan_summary": "",
 "tasks": [
   {{
     "day": 1,
     "title": "",
     "instructions": "",
     "expected_outcome": ""
   }}
 ]
}}"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role":"user","content":prompt}]
    )

    return response.choices[0].message.content