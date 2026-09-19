# Please install OpenAI SDK first: `pip3 install openai`
import os
from openai import OpenAI
import json

client = OpenAI(
    api_key = os.getenv("DEEPSEEK_API_KEY", "").strip(),
    base_url="https://api.deepseek.com")


def parse_audit_results_json():
    filename = "backend/uploads/jsons/sample_nike_results.json"
    #open json file, read the json and return dict
    with open(filename, "r") as f:
        data = f.read()
    return json.loads(data)



def _prompt(audit_payload):
    prompt = f"""
    You are a senior marketing and web performance consultant.

    Turn the following website audit results into plain-English, business-friendly language for a non-technical owner.
    Focus on:
    - what matters most for growth and trust
    - why it matters to customers
    - what action to take next
    - keep suggestions practical and concise

    Use this actual audit data:
    {audit_payload}

    Return valid JSON only with this exact schema:
    {{
        "priority": "high|medium|low",
        "headline": "short sentence",
        "summary": "2-3 sentence explanation",
        "business_score": 0-100,
        "findings": [
            {{
            "theme": "speed|visibility|trust|clarity|accessibility|value|dead_ends|visuals",
            "headline": "short headline",
            "business_impact": "plain English impact",
            "recommended_action": "actionable recommendation",
            "weight": 1-20
            }}
        ],
        "next_steps": ["string", "string", "string"]
        }}
    """
    return prompt

audit_results = parse_audit_results_json()
prompt = _prompt(audit_results)

response = client.chat.completions.create(
    model="deepseek-flash",
    messages=[
        {
                        "role": "system",
                        "content": "You write concise, business-friendly website audit summaries. Return valid JSON only."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
    ],
    stream=False,
    reasoning_effort="high",
    extra_body={"thinking": {"type": "enabled"}}
)

print(response.choices[0].message.content)