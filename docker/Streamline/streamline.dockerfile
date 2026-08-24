FROM python:3.12-slim

COPY ./Streamline/requirements.txt /requirements.txt
RUN pip install -r /requirements.txt

ENV DEBIAN_FRONTEND=noninteractive
RUN apt update && apt install -y ffmpeg

CMD ["python", "/Streamline/Streamline.py"]