FROM ghcr.io/merklebot/hackathon-amd-image:master as build

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

ENV SPEECH_KEY="b2079993b3e64e7f9631296aa9859349"
ENV SPEECH_REGION="eastus"
ENV OPENAI_API_KEY="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"

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
