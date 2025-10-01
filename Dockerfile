FROM ghcr.io/mgoltzsche/beets-plugins:0.18.1

# Install bats
USER root:root
ARG BATS_VERSION=1.10.0
RUN set -eux; \
	wget -qO - https://github.com/bats-core/bats-core/archive/refs/tags/v${BATS_VERSION}.tar.gz | tar -C /tmp -xzf -; \
	/tmp/bats-core-$BATS_VERSION/install.sh /opt/bats; \
	ln -s /opt/bats/bin/bats /usr/local/bin/bats; \
	rm -rf /tmp/bats-core-$BATS_VERSION

# Install beets patch + yt-dlp upgrade
RUN set -eux; \
	BUILD_DEPS='git'; \
	apk add --update --no-cache $BUILD_DEPS; \
	python3 -m pip install \
		git+https://github.com/beetbox/beets.git@a1c0ebdeef267e227c26f9defc93799c86c8fe54#egg=beets \
		ytmusicapi==1.9.1 \
		yt-dlp==2025.01.26; \
	apk del --purge $BUILD_DEPS

# Install beets-autogenre from source
COPY dist /plugin/dist
RUN python -m pip install /plugin/dist/*
COPY example_beets_config.yaml /etc/beets/default-config.yaml
USER beets:beets
