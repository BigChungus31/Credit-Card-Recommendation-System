from flask import Flask, request, jsonify
from flask_cors import CORS
import uuid
import os
import requests
import json
import re
from typing import Dict, List, Optional
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

# Store active sessions
sessions = {}

groq_api_key = os.getenv("GROQ_API_KEY")
if groq_api_key:
    os.environ["GROQ_API_KEY"] = groq_api_key
else:
    print("Warning: GROQ_API_KEY not found in .env file")

class UserProfile:
    def __init__(self):
        self.monthly_income: Optional[int] = None
        self.spending_categories: List[str] = []
        self.preferred_benefits: List[str] = []
        self.annual_fee_preference: Optional[str] = None
        self.additional_context: str = ""

    def is_ready_for_recommendations(self) -> bool:
        return (
            self.monthly_income is not None and
            len(self.spending_categories) > 0 and
            len(self.preferred_benefits) > 0 and
            self.annual_fee_preference is not None
        )

    def to_dict(self) -> Dict:
        return {
            "monthly_income": self.monthly_income,
            "spending_habits": self.spending_categories,
            "preferred_benefits": self.preferred_benefits,
            "annual_fee_preference": self.annual_fee_preference
        }

class ConversationalCreditCardAssistant:
    def __init__(self):
        self.llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            temperature=0.2,
            max_tokens=2048
        )
        self.user_profile = UserProfile()
        self.conversation_history = []
        self.api_url = "http://localhost:8002/recommendations"

        self.spending_categories = ["fuel", "groceries", "dining", "travel", "online", "offline", "shopping", "utilities", "entertainment"]
        self.benefit_types = ["cashback", "rewards", "lounge", "travel", "fuel", "dining", "shopping", "entertainment"]
        self.fee_preferences = ["no fee", "low fee", "any"]

    def safe_int_conversion(self, value, default=0):
        try:
            if isinstance(value, str):
                if value.lower() in ['free', 'nil', 'na', 'none']:
                    return 0
                value = re.sub(r'[^\d]', '', value)
                return int(value) if value else default
            return int(value) if value is not None else default
        except:
            return default

    def extract_user_intent(self, user_message: str) -> Dict:
        system_prompt = f"""You are an expert at extracting financial preferences from natural language.

Analyze the user's message and extract:
1. Monthly income (if mentioned) - convert to number
2. Spending categories - map to: {', '.join(self.spending_categories)}
3. Preferred benefits - map to: {', '.join(self.benefit_types)}
4. Annual fee preference - classify as: no fee, low fee, or any
5. Additional context - any other relevant information

Current user profile:
- Income: {self.user_profile.monthly_income}
- Spending: {self.user_profile.spending_categories}
- Benefits: {self.user_profile.preferred_benefits}
- Fee preference: {self.user_profile.annual_fee_preference}

Return ONLY a JSON object with these keys:
{{
    "income": null or number,
    "spending": ["category1", "category2"],
    "benefits": ["benefit1", "benefit2"],
    "fee_preference": null or "no fee"/"low fee"/"any",
    "context": "additional information"
}}

Examples:
"I earn 75000 per month and spend mostly on travel and dining" → {{"income": 75000, "spending": ["travel", "dining"], "benefits": [], "fee_preference": null, "context": ""}}
"I want lounge access and fuel benefits but don't want high annual fees" → {{"income": null, "spending": [], "benefits": ["lounge", "fuel"], "fee_preference": "low fee", "context": ""}}
"""

        try:
            response = self.llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_message)
            ])

            extracted = json.loads(response.content.strip())
            return extracted
        except Exception as e:
            print(f"Extraction error: {e}")
            return {"income": None, "spending": [], "benefits": [], "fee_preference": None, "context": user_message}

    def update_user_profile(self, extracted_data: Dict):
        if extracted_data.get("income"):
            self.user_profile.monthly_income = extracted_data["income"]

        if extracted_data.get("spending"):
            for category in extracted_data["spending"]:
                if category not in self.user_profile.spending_categories:
                    self.user_profile.spending_categories.append(category)

        if extracted_data.get("benefits"):
            for benefit in extracted_data["benefits"]:
                if benefit not in self.user_profile.preferred_benefits:
                    self.user_profile.preferred_benefits.append(benefit)

        if extracted_data.get("fee_preference"):
            self.user_profile.annual_fee_preference = extracted_data["fee_preference"]

        if extracted_data.get("context"):
            self.user_profile.additional_context += " " + extracted_data["context"]

    def generate_follow_up(self) -> str:
        missing_info = []

        if self.user_profile.monthly_income is None:
            missing_info.append("monthly income")
        if not self.user_profile.spending_categories:
            missing_info.append("spending patterns")
        if not self.user_profile.preferred_benefits:
            missing_info.append("desired benefits")
        if self.user_profile.annual_fee_preference is None:
            missing_info.append("annual fee preference")

        if not missing_info:
            return self.get_recommendations()

        current_profile = f"""
Current information:
- Monthly Income: {'Rs. ' + str(self.user_profile.monthly_income) if self.user_profile.monthly_income else 'Not provided'}
- Spending Categories: {', '.join(self.user_profile.spending_categories) if self.user_profile.spending_categories else 'Not provided'}
- Preferred Benefits: {', '.join(self.user_profile.preferred_benefits) if self.user_profile.preferred_benefits else 'Not provided'}
- Annual Fee Preference: {self.user_profile.annual_fee_preference or 'Not provided'}
"""

        system_prompt = f"""You are a friendly credit card advisor. Based on the user's profile and missing information, ask natural follow-up questions.

{current_profile}

Missing information: {', '.join(missing_info)}

Generate a conversational response that:
1. Acknowledges what the user has shared
2. Naturally asks for the most important missing information
3. Provides examples or context to help the user respond
4. Keeps the tone warm and helpful

Don't ask for all missing info at once. Focus on the most critical piece."""

        try:
            response = self.llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content="Generate appropriate follow-up question")
            ])
            return response.content.strip()
        except Exception as e:
            return f"I'd love to help you find the perfect card! Could you tell me about your {missing_info[0]}?"

    def get_recommendations(self) -> str:
        try:
            response = requests.post(
                self.api_url,
                json=self.user_profile.to_dict(),
                headers={"Content-Type": "application/json"},
                timeout=15
            )

            if response.status_code == 200:
                result = response.json()
                print(f"API Response: {result}")
                if "recommendations" in result and result["recommendations"]:
                    return self.format_recommendations(result["recommendations"])
                else:
                    return "I couldn't find any cards that perfectly match your criteria. Let me suggest some popular options based on your income range, or would you like to adjust your preferences?"
            else:
                print(f"API Error: Status {response.status_code}, Response: {response.text}")
                return "I'm having trouble accessing the card database right now. Let me give you some general recommendations based on your profile."

        except requests.exceptions.ConnectionError:
            return "I'm having trouble connecting to the card database. Please ensure the backend service is running on localhost:8002."
        except Exception as e:
            print(f"Recommendation fetch error: {str(e)}")
            return f"Something went wrong while fetching recommendations: {str(e)}"

    def format_recommendations(self, cards: List[Dict]) -> str:
        if not cards:
            return "No suitable cards found based on your preferences."

        try:
            valid_cards = []
            for card in cards:
                try:
                    match_score = self.safe_int_conversion(card.get('match_score', 0))
                    card['_numeric_match_score'] = match_score
                    valid_cards.append(card)
                except Exception as e:
                    print(f"Skipping invalid card data: {e}")
                    continue

            top_cards = sorted(valid_cards, key=lambda x: x.get('_numeric_match_score', 0), reverse=True)[:3]
        except Exception as e:
            print(f"Sorting error: {e}")
            top_cards = cards[:3]

        output = "Perfect Matches for You!\n\n"

        for i, card in enumerate(top_cards):
            try:
                card_name = card.get('card_name', 'Unknown Card')
                bank = card.get('bank', 'Unknown Bank')
                match_score = card.get('_numeric_match_score', card.get('match_score', 0))
                eligibility = card.get('eligibility_met', False)

                if i == 0:
                    output += f"TOP RECOMMENDATION: {card_name}\n"
                    output += f"{bank}\n\n"

                    output += "Why this card?\n"
                    if self.user_profile.monthly_income:
                        output += f"Matches your income level (~Rs.{self.user_profile.monthly_income:,})\n"

                    if card.get('matched_categories'):
                        matched = ', '.join([cat.title() for cat in card['matched_categories']])
                        user_spending = ', '.join([cat.title() for cat in self.user_profile.spending_categories])
                        output += f"Accelerated rewards on {matched} (your spending focus: {user_spending})\n"

                    if 'lounge' in self.user_profile.preferred_benefits and 'lounge' in str(card).lower():
                        output += "Premium lounge access included\n"

                    annual_fee_num = self.safe_int_conversion(card.get('annual_fee', 0))
                    if self.user_profile.annual_fee_preference == "no fee" and annual_fee_num == 0:
                        output += "No annual fee (as requested)\n"
                    elif self.user_profile.annual_fee_preference == "low fee" and annual_fee_num < 5000:
                        output += f"Reasonable annual fee: Rs.{annual_fee_num:,}\n"

                    output += f"Match Score: {match_score}/100\n"
                    output += f"Eligibility: {'You qualify!' if eligibility else 'May need verification'}\n\n"

                    if 'annual_fee' in card:
                        fee_num = self.safe_int_conversion(card['annual_fee'])
                        if fee_num == 0:
                            output += "Annual Fee: FREE\n"
                        else:
                            output += f"Annual Fee: Rs.{fee_num:,}"
                            if 'fee_waiver' in str(card).lower():
                                output += " (waiver conditions apply)"
                            output += "\n"

                    if card.get('key_features'):
                        output += "Key Benefits:\n"
                        features = card['key_features'] if isinstance(card['key_features'], list) else [card['key_features']]
                        for feature in features[:5]:
                            output += f"• {feature}\n"

                    output += "\n" + "─" * 50 + "\n\n"

                else:
                    output += f"Alternative #{i}: {card_name} - {bank}\n"
                    if card.get('key_features'):
                        features = card['key_features'] if isinstance(card['key_features'], list) else [card['key_features']]
                        if features:
                            output += f"• {features[0]}\n"
                    elif card.get('matched_categories'):
                        output += f"• Great for {', '.join(card['matched_categories'])}\n"

                    fee_num = self.safe_int_conversion(card.get('annual_fee', 0))
                    output += f"• Annual Fee: {'FREE' if fee_num == 0 else f'Rs.{fee_num:,}'}\n"
                    output += f"• Match Score: {match_score}/100\n\n"

            except Exception as e:
                print(f"Error formatting card {i}: {e}")
                continue

        output += "Want to explore more options? Tell me if you'd like to adjust any preferences or need cards for specific use cases!"

        return output

    def process_message(self, user_message: str) -> str:
        self.conversation_history.append(("user", user_message))

        extracted_data = self.extract_user_intent(user_message)
        self.update_user_profile(extracted_data)

        if self.user_profile.is_ready_for_recommendations():
            response = self.get_recommendations()
        else:
            response = self.generate_follow_up()

        self.conversation_history.append(("assistant", response))
        return response

    def start_conversation(self) -> str:
        greeting = """Hi there! I'm your personal credit card advisor!

I'm here to help you find the perfect credit card that matches your lifestyle and financial goals. Instead of filling out boring forms, just tell me about yourself naturally!

For example, you could say:
• "I earn around 60K per month and spend mostly on groceries and fuel"
• "I travel a lot for work and want lounge access but don't want expensive annual fees"
• "I'm looking for a cashback card for online shopping"

What brings you here today? Tell me about your spending habits or what you're looking for in a credit card!"""

        return greeting

# Flask API Routes
@app.route('/start', methods=['POST'])
def start_conversation():
    session_id = str(uuid.uuid4())
    assistant = ConversationalCreditCardAssistant()
    sessions[session_id] = assistant
    
    return jsonify({
        'session_id': session_id,
        'response': assistant.start_conversation(),
        'profile_complete': False
    })

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    session_id = data.get('session_id')
    message = data.get('message', '')
    
    if session_id not in sessions:
        return jsonify({'error': 'Session not found'}), 400
    
    assistant = sessions[session_id]
    response = assistant.process_message(message)
    
    return jsonify({
        'response': response,
        'profile_complete': assistant.user_profile.is_ready_for_recommendations(),
        'user_profile': assistant.user_profile.to_dict()
    })

@app.route('/restart', methods=['POST'])
def restart():
    data = request.json
    session_id = data.get('session_id')
    
    assistant = ConversationalCreditCardAssistant()
    sessions[session_id] = assistant
    
    return jsonify({
        'response': assistant.start_conversation(),
        'profile_complete': False
    })
    
@app.route('/')
def home():
    return "Flask Credit Card API is running!"

@app.route('/test')
def test():
    return jsonify({"status": "API is working", "endpoints": ["/start", "/chat", "/restart"]})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
