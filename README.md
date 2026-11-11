# Pool

An AI agent that finds a gift, pools money from friends through PayPal, and only charges when the goal is met. Built for the PayPal AI Hackathon.

**Live demo:** https://pool-patk.onrender.com
The demo runs on Render's free plan, so the first load after a quiet period can take about a minute.

## The problem
Group gifts are messy. Someone fronts the money, chases friends in chat, and the order stalls if not enough people pay.

## How it works
1. You tell the agent what to buy ("Gift for my friend Priya, a woman who loves hiking, $150 budget").
2. The agent searches products with **Channel3**, picks one within budget, and creates a funding pool.
3. Friends contribute through **PayPal**. Each contribution is an authorization, a hold on their money.
4. When the holds reach the goal, the app captures every payment. If the deadline passes underfunded, it voids every hold, so nobody is charged.
5. Every step is written to an activity log shown in the app.

## Safety design
- The AI has three tools: search products, create a pool, and check pool status. It has **no tool that can move money**.
- Capture and void run only from plain code, after a deterministic check: the pool is open, every authorization is present and unique, and the total meets the goal.
- Prices come from Channel3 results, never from the model, and a pool must fit the user's budget.
- 7 automated tests cover the safety check (underfunded, closed, duplicate, and missing-authorization cases).

## Tools used
- **PayPal** (sandbox): Orders API with `AUTHORIZE`, plus authorization capture and void
- **Channel3**: product search, using the cheapest in-stock offer across retailers
- **Amazon Bedrock** (Nova Lite): the agent's reasoning and tool calling
- **Render**: hosting for the live demo
- Python, Streamlit, SQLAlchemy, SQLite, Pytest

## Project layout
```
app/
  agent.py          Bedrock agent and its three tools
  paypal.py         PayPal authorize, capture, and void
  products.py       Channel3 product search
  pool_service.py   contributions, verification, capture, void, deadlines
  db.py             pools, contributions, and activity log tables
streamlit_app.py    the web interface
tests/              safety-check tests
```

## Try the live demo
1. Open the live demo and go to **Ask the agent**. Describe what to buy and click the button.
2. Go to **Pools**, choose the pool, enter a name and an amount, and click **Contribute with PayPal**.
3. Pay with a **PayPal sandbox buyer account**. Sandbox login details are in the Devpost testing instructions, or you can create your own at developer.paypal.com.
4. When contributions reach the target, every hold is captured.
5. To see the failure path, open **Demo controls** and click **Close this pool now** on a partly funded pool. Every hold is released.

## Run it locally
1. Clone the repo and create a virtual environment:
   ```
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. Copy `.env.example` to `.env` and fill in your own keys:
   - PayPal sandbox Client ID and Secret (developer.paypal.com)
   - A Channel3 API key (trychannel3.com/developers)
   - AWS credentials with access to Amazon Bedrock and the Nova Lite model
3. Create one Business and two Personal sandbox accounts in the PayPal developer dashboard.
4. Start the app:
   ```
   streamlit run streamlit_app.py --server.port 8501
   ```
5. Run the tests:
   ```
   python -m pytest -q
   ```

## Deploying
On Render, create a Web Service from this repo with:
- Build command: `pip install -r requirements.txt`
- Start command: `streamlit run streamlit_app.py --server.port $PORT --server.address 0.0.0.0 --server.headless true`
- Environment variables: `PAYPAL_CLIENT_ID`, `PAYPAL_SECRET`, `CHANNEL3_API_KEY`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`, and `APP_BASE_URL` (the service's public URL)

## Notes and limits
- All payments use the PayPal **sandbox** with test money. No real purchase is made; the product link shows what would be bought.
- Data is stored in SQLite, so it can reset when the free-plan service restarts.
- Pool deadlines are checked by a background loop every 30 seconds while the app is running.

## License
MIT