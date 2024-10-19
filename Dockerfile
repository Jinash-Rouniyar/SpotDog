FROM ghcr.io/merklebot/hackathon-amd-image:master as build

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

ENV SPEECH_KEY="b2079993b3e64e7f9631296aa9859349"
ENV SPEECH_REGION="eastus"

ARG TARGETPLATFORM
ARG BUILDPLATFORM
ARG TARGETOS
ARG TARGETARCH

ARG Version
ARG GitCommit
RUN echo "I am running on $BUILDPLATFORM, building for $TARGETPLATFORM" 


COPY requirements.txt requirements.txt
RUN python3.8 -m pip install -r requirements.txt
COPY . .

CMD ["python3.8", "main.py"]
