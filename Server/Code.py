import json
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
import pandas as pd

app = FastAPI(title="Credit Card Recommendation API")

with open('../Dataset/credit_cards_dataset.json', 'r') as f:
    credit_cards = json.load(f)

    if isinstance(raw_data, dict) and 'cards' in raw_data:
        cards_data = raw_data['cards']
    elif isinstance(raw_data, list):
        cards_data = raw_data
    else:
        cards_data = []

    print(f"Loaded {len(cards_data)} cards")
    if cards_data:
        print(f"Sample card keys: {list(cards_data[0].keys())}")

class UserInput(BaseModel):
    monthly_income: int
    spending_habits: List[str]
    preferred_benefits: List[str]
    annual_fee_preference: Optional[str] = None

class CardRecommendation(BaseModel):
    card_name: str
    bank: str
    match_score: int
    eligibility_met: bool
    matched_categories: List[str]
    matched_benefits: List[str]
    annual_fee: str
    key_features: List[str]
    justification: str

class RecommendationResponse(BaseModel):
    recommendations: List[CardRecommendation]
    total_cards_evaluated: int

def calculate_match_score(card: Dict, user: UserInput) -> tuple:
    score = 0
    matched_categories = []
    matched_benefits = []

    if not isinstance(card, dict):
        return 0, [], [], False

    eligibility_text = card.get('eligibility', '').lower()
    min_income = 0
    if 'monthly income' in eligibility_text:
        import re
        numbers = re.findall(r'[\d,]+', eligibility_text)
        if numbers:
            min_income = int(numbers[0].replace(',', ''))
    elif 'annual income' in eligibility_text:
        import re
        numbers = re.findall(r'[\d,]+', eligibility_text)
        if numbers:
            min_income = int(numbers[0].replace(',', '')) // 12

    eligibility_met = user.monthly_income >= min_income
    if eligibility_met:
        score += 2

    reward_rate = card.get('reward_rate', '').lower()
    user_categories = [cat.lower() for cat in user.spending_habits]

    category_mapping = {
        'fuel': ['fuel', 'petrol', 'gas'],
        'groceries': ['grocery', 'supermarket', 'food'],
        'dining': ['dining', 'restaurant', 'food'],
        'online': ['online', 'e-commerce'],
        'offline': ['offline', 'retail'],
        'travel': ['travel', 'flight', 'hotel']
    }

    for user_cat in user_categories:
        mapped_cats = category_mapping.get(user_cat, [user_cat])
        if any(cat in reward_rate for cat in mapped_cats):
            score += 3
            matched_categories.append(user_cat)

    user_benefits = [ben.lower() for ben in user.preferred_benefits]
    card_perks = [perk.lower() for perk in card.get('perks', [])]
    reward_type = card.get('reward_type', '').lower()

    benefit_mapping = {
        'cashback': ['cashback', 'cash back'],
        'rewards': ['reward', 'points'],
        'lounge': ['lounge'],
        'travel': ['travel', 'insurance'],
        'fuel': ['fuel', 'surcharge']
    }

    for user_ben in user_benefits:
        mapped_bens = benefit_mapping.get(user_ben, [user_ben])
        if any(ben in reward_type for ben in mapped_bens) or any(ben in ' '.join(card_perks) for ben in mapped_bens):
            score += 3
            matched_benefits.append(user_ben)

    if user.annual_fee_preference:
        annual_fee = card.get('annual_fee', 0)
        if user.annual_fee_preference.lower() == "no fee" and annual_fee == 0:
            score += 2
        elif user.annual_fee_preference.lower() == "low fee" and annual_fee <= 1000:
            score += 1

    return score, matched_categories, matched_benefits, eligibility_met

@app.post("/recommendations", response_model=RecommendationResponse)
async def get_recommendations(user_input: UserInput):
    try:
        recommendations = []

        for card in cards_data:
            score, matched_cats, matched_bens, eligible = calculate_match_score(card, user_input)

            justification = f"Score: {score}/10. "
            if eligible:
                justification += "Income requirement met. "
            else:
                justification += "Income requirement not met. "

            if matched_cats:
                justification += f"Matches spending: {', '.join(matched_cats)}. "
            if matched_bens:
                justification += f"Matches benefits: {', '.join(matched_bens)}. "

            recommendations.append(CardRecommendation(
                card_name=card.get('name', 'Unknown Card'),
                bank=card.get('issuer', 'Unknown Bank'),
                match_score=score,
                eligibility_met=eligible,
                matched_categories=matched_cats,
                matched_benefits=matched_bens,
                annual_fee=f"₹{card.get('annual_fee', 0)}",
                key_features=card.get('perks', [])[:3],
                justification=justification
            ))

        recommendations.sort(key=lambda x: x.match_score, reverse=True)
        top_recommendations = recommendations[:5]

        return RecommendationResponse(
            recommendations=top_recommendations,
            total_cards_evaluated=len(cards_data)
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    return {"message": "Credit Card Recommendation API", "status": "active"}

@app.get("/cards")
async def get_all_cards():
    return {"total_cards": len(cards_data), "cards": [card['name'] for card in cards_data]}

if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()

    config = uvicorn.Config(app, host="0.0.0.0", port=8002, log_level="info")
    server = uvicorn.Server(config)

    import asyncio
    import threading

    def start_server():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(server.serve())

    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()

    import time
    time.sleep(2)
    print("Server is running on http://localhost:8002")