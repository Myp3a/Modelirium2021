import requests
import sys
import random

uid = sys.argv[1]
count = int(sys.argv[2])

for i in range(count):
    with requests.Session() as sess:
        sess.post(f'http://127.0.0.1:8080/{uid}/data',data={'upper':random.randint(100,160),'lower':random.randint(80,100),'pulse':random.randint(50,70)})