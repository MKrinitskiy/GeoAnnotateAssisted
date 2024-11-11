FROM python:3.10.15-slim-bullseye

# RUN apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 605C66F00D6C9793 0E98404D386FA1D9 648ACFD622F3D138 6ED0E7B82643E131 F8D2585B8783D481

RUN apt update; \
    apt install -y --no-install-recommends \
    apt-utils \
    build-essential \
    ffmpeg \
    git \
    vim \
    openssh-server \
    tmux \
    sudo \
    ; \
    rm -rf /var/lib/apt/lists/*

RUN pip install wheel && pip install setuptools==59.5.0
COPY ./requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt && rm -r /tmp/requirements.txt

# COPY . /code
WORKDIR /code

CMD ["bash"]

