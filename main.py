from LLM import chat

user_pass = input("Enter user password: ")
while True:
    query = input("Your Message: ")
    if query.lower() in ["exit", "quit"]:
        break
    print(chat(user_pass, query))


