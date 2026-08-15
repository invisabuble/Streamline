FROM python:3.12-slim

COPY ./Streamline/requirements.txt /requirements.txt
RUN pip install -r /requirements.txt

CMD ["python", "/Streamline/Streamline.py"]