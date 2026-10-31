from app.agent import run_agent
from app.db import init_db

init_db()
request = input("What do you want to buy together? ")
print("\nAgent steps:")
answer = run_agent(request)
print("\nAgent:", answer)