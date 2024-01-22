FROM ubuntu
ARG DRIVER
ARG MONITOR_WIDTH=1920
ARG MONITOR_HEIGHT=1080
ARG MONITOR_DEPTH=24

SHELL ["/bin/bash", "-c"]

RUN set -euxo pipefail; \
    apt-get -y update; \
    apt-get -y dist-upgrade; \
    DEBIAN_FRONTEND=noninteractive apt-get -y install \
      fonts-ipaexfont \
      fonts-ipafont \
      gnupg \
      mesa-utils \
      novnc \
      ${DRIVER:+${DRIVER}} \
      tigervnc-standalone-server \
      wget \
      xfonts-base; \
    wget -qO - 'https://dl-ssl.google.com/linux/linux_signing_key.pub' | apt-key add -; \
    echo 'deb http://dl.google.com/linux/chrome/deb/ stable main' >> /etc/apt/sources.list.d/google.list; \
    apt-get update; \
    DEBIAN_FRONTEND=noninteractive apt-get -y install google-chrome-stable; \
    apt-get clean && rm -rf /var/lib/apt/lists/*; \
    useradd -ms /bin/bash ubuntu

ENV DBUS_SYSTEM_BUS_ADDRESS=unix:path=/host/run/dbus/system_bus_socket

USER ubuntu
WORKDIR /home/ubuntu

RUN set -euxo pipefail; \
    mkdir "$HOME/.vnc"
