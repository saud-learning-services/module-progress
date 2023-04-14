import logging
import sys
import os
from canvasapi import Canvas
from dotenv import load_dotenv

load_dotenv() 

# logging
logger = logging.getLogger("canvasapi")
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

handler.setLevel(logging.DEBUG)
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

API_URL = "https://canvas.ubc.ca" 
API_KEY = os.getenv('CANVAS_API_TOKEN')


canvas = Canvas(API_URL, API_KEY)

print("BASE URL:")
print(canvas._Canvas__requester.base_url)

me = canvas.get_current_user()

print("Response:")
print(me)
