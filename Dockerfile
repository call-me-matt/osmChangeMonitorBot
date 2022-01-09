FROM python

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip3 install --no-cache-dir -r requirements.txt

#COPY ./src .

CMD [ "python", "./osmChangesetsBot.py" ]
