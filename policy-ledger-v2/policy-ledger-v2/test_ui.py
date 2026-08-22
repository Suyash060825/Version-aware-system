import requests
import re
import os

with open("templates/employee/chat.html", "r") as f:
    content = f.read()
    
# check if X-CSRFToken is there
if "X-CSRFToken" in content:
    print("X-CSRFToken header is successfully inserted in chat.html")
else:
    print("Missing X-CSRFToken")
