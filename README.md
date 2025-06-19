# Credit-Card-Recommendation-System
AI-powered credit card recommendation system

# Credit Card Recommendation System

An AI-powered credit card recommendation system that helps users find the best credit cards based on their financial profile and preferences.

# Features

- Intelligent credit card recommendations based on user profile
- Interactive web interface
- Real-time card matching algorithm
- Comprehensive card database
- User-friendly recommendation explanations

# Tech Stack
Frontend:
- HTML

Backend:
- Python
- Flask and FastAPI

AI/ML:
- Groq LLM

Database:
- JSON dataset created consisting of 24 credit cards

# Project Structure

CreditCard → Backend → .env, app.py, requirements.txt
           → Dataset → Code.py, credit_cards_dataset.csv
           → Frontend → index.html
           → Server → Code.py, main.py
           → README.md
          
# Prerequisites
- Python 3.8+
- pip package manager

# Installation

1. Clone the repository
   bash
   git clone https://github.com/BigChungus31/credit-card-recommendation-system.git
   cd credit-card-recommendation-system
   
2. Set up Backend
   ```bash
   cd Backend
   pip install -r requirements.txt  

3. Configure Environment Variables
   - Create a `.env` file in the Backend directory
   - Add your API keys:
   ```
   GROQ_API_KEY=your_groq_key_here

4. Run the Backend Server
   ```bash
   python app.py   

5. Open Frontend
   - Navigate to the Frontend folder
   - Open `index.html` in your browser
   - Or serve it using a local server:
   ```bash
   python -m http.server 8000   

6. Access the Application
   - Frontend: `http://localhost:8000`
   - Backend API: `http://localhost:5000` (or your specified port)

# Agent Flow and Architecture

System Architecture
```
User Input → Frontend → Backend API → AI Agent → Recommendation Engine → Response


Agent Flow
1. Input Processing: User provides financial information and preferences
2. Data Validation: System validates and sanitizes user input
3. Profile Analysis: AI agent analyzes user's financial profile
4. Card Matching: Algorithm matches user profile with card database
5. Ranking: Cards are ranked based on suitability scores
6. Response Generation: AI generates personalized explanations
7. Frontend Display: Results presented to user with explanations
```
# Profile Analysis Prompt:
```
Analyze the user's financial profile including:
- Income level: {income}
- Credit score: {credit_score}
- Spending categories: {spending_pattern}
- Financial goals: {goals}
```
# Recommendation Prompt:
```
Based on the user profile analysis, recommend the top 3 credit cards from our database.
Consider:
- Reward compatibility with spending patterns
- Fee structure alignment with usage
- Credit requirements match
- Special benefits relevance
```
# Dataset

The system uses a comprehensive credit card database containing:
- Card names and issuers
- Annual fees and interest rates
- Reward structures and categories
- Sign-up bonuses
- Credit score requirements
- Special features and benefits

# Author

**Abhimanyu Choudhry**
- GitHub: [@BigChungus31](https://github.com/BigChungus31)
- Email: choudhryabhimanyu31@gmail.com
