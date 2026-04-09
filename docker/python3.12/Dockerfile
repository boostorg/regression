FROM alpine:3.23
CMD ["/bin/sh"]
RUN apk add --no-cache python3 py3-pip linux-headers git rsync openssh g++ zlib-dev \
    && ln -sf python3 /usr/bin/python \
    && ln -sf pip3 /usr/bin/pip
WORKDIR /root
