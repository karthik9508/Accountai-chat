import json
from datetime import date
from django.conf import settings
from google import genai
from google.genai import types

def call_ai_parser(message_text, base_currency='INR'):
    """
    Calls Gemini to parse a natural language transaction into a structured JSON payload.
    Returns (json_dict, None) on success, or (None, error_string) on failure.
    """
    if not settings.GEMINI_API_KEY:
        print("Warning: GEMINI_API_KEY is not set.")
        return None, "GEMINI_API_KEY is missing from your .env file or hasn't been loaded. Note: You must restart your server after adding it to .env!"

    try:
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        
        today_str = date.today().isoformat()
        
        system_prompt = f"""
You are an AI financial copilot. Your job is to extract structured data from the user's natural language message and classify their intent.

You must output a JSON envelope strictly matching this schema:
{{
    "intent": "transaction" | "report" | "invoice",
    "payload": {{ ... }}
}}

Depending on the intent, the payload must look like this:

1. If the user wants to record a transaction (e.g. "Spent 500 on fuel"):
"intent": "transaction"
"payload": {{
    "kind": "income" or "expense",
    "amount": "<decimal amount>",
    "currency": "<3-letter currency code, default {base_currency}>",
    "occurred_on": "<YYYY-MM-DD format date. Today is {today_str}>",
    "category_name": "<String describing the category>",
    "counterparty": "<String describing the person/business involved, or empty string>",
    "note": "<Short string description>"
}}

2. If the user wants a financial report (e.g. "How much did I spend on AWS?"):
"intent": "report"
"payload": {{
    "kind": "income" | "expense" | "all",
    "start_date": "<YYYY-MM-DD, default 2000-01-01 if unspecified>",
    "end_date": "<YYYY-MM-DD, default {today_str} if unspecified>",
    "category": "<Specific category name if mentioned, or empty string>"
}}

3. If the user wants to generate an invoice (e.g. "Create an invoice for Karthik for 5000"):
"intent": "invoice"
"payload": {{
    "customer_name": "<String name of the customer>",
    "amount": "<decimal amount string>",
    "description": "<String description for the invoice line item>"
}}

Return ONLY the raw JSON object. Do not include markdown formatting like ```json ... ```.
"""
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[message_text.strip()],
            config=types.GenerateContentConfig(
                system_instruction=system_prompt.strip(),
                temperature=0.0,
            )
        )
        
        content = response.text.strip()
        
        # In case the model returns markdown code block anyway, strip it
        if content.startswith('```json'):
            content = content[7:]
        if content.startswith('```'):
            content = content[3:]
        if content.endswith('```'):
            content = content[:-3]
            
        parsed_json = json.loads(content.strip())
        return parsed_json, None
        
    except Exception as e:
        err = f"Error calling AI parser: {e.__class__.__name__} - {str(e)}"
        print(err)
        return None, err
