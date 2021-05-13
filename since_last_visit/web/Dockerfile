FROM python:3.9-slim-buster
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
COPY . /app
WORKDIR /app
RUN apt-get update && apt-get install -y git
RUN pip install -r requirements.txt
EXPOSE 8501
CMD ["streamlit", "run", "since_last_visit.py"]
