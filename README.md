#Pool
# Pool

An AI agent that finds a gift, pools money from friends through PayPal, and only charges when the goal is met. Built for the PayPal AI Hackathon.

## How it works
1. You tell the agent what to buy ("Gift for my friend Priya, $150 budget").
2. The agent searches products with **Channel3**, picks one within budget, and creates a funding pool.
3. Friends contribute through **PayPal** (sandbox). Each contribution is an authorization, a hold on their money.
4. If the goal is reached, the app captures every hold. If the deadline passes underfunded, it voids every hold and nobody is charged.

## Safety design
- The AI has three tools: search products, create a pool, and check pool status. It has no tool that can move money.
- Capture and void run only from plain code, after a deterministic check: the pool is open, every authorization is present and unique, and the total meets the goal.
- Prices come from Channel3 results, never from the model, and a pool must fit the user's budget.
- Every action is written to an activity log shown in the app.

## Tech
Python, Streamlit, Amazon Bedrock (Nova Lite), PayPal Orders and Payments APIs (sandbox), Channel3 product search, SQLite, SQLAlchemy, Pytest.

## Setup
1. Clone the repo and create a virtual environment:
   ```
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. Copy `.env.example` to `.env` and fill in your own keys:
   - PayPal sandbox Client ID and Secret (developer.paypal.com)
   - A Channel3 API key (trychannel3.com/developers)
   - AWS credentials with access to Amazon Bedrock and the Nova Lite model in your region
3. Create one Business and two Personal sandbox accounts in the PayPal developer dashboard.
4. Run the app:
   ```
   streamlit run streamlit_app.py --server.port 8501
   ```
5. Run the tests:
   ```
   python -m pytest -q
   ```

## Using the demo
1. On "Ask the agent", describe what to buy and click the button.
2. On "Pools", choose the pool, enter a name and amount, and pay through PayPal using a sandbox buyer login.
3. When contributions reach the goal, every hold is captured. Use "Demo controls" to close a pool early and see unfunded holds released.

## Notes
- All payments use the PayPal sandbox with test money. No real purchase is made; the product link shows what would be bought.

## License
MIT