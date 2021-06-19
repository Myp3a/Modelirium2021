import requests
import sys
import random
import time

uid = sys.argv[1]
count = int(sys.argv[2])
try:
    state = sys.argv[3]
except:
    state = None

#for i in range(count):
while True:
    with requests.Session() as sess:
        sess.post(f'http://127.0.0.1:8080/{uid}/data',data={'upper':random.randint(100,160),'lower':random.randint(70,110),'pulse':random.randint(50,85),'state':state})
        time.sleep(1)