PYPI_REPO=https://upload.pypi.org/legacy/
define DOCKERFILE
FROM python:3.9-alpine
RUN python -m pip install twine==4.0.2
endef
export DOCKERFILE
BEETS_IMG=beets-autogenre
BUILD_IMG=beets-autogenre-build
DOCKER_OPTS=--rm -u `id -u`:`id -g` \
                -v "`pwd`:/work" -w /work \
                --entrypoint sh $(BUILD_IMG) -c

.PHONY: wheel
wheel: clean python-container
	docker run $(DOCKER_OPTS) 'python3 setup.py bdist_wheel'

.PHONY: test
test: beets-container
	# Run unit tests
	mkdir -p data/beets
	@docker run --rm -u `id -u`:`id -g` \
		-v "`pwd`:/plugin" -w /plugin \
		-v "`pwd`/data:/data" \
		--entrypoint sh $(BEETS_IMG) -c \
		'set -x; python -m unittest discover /plugin/tests'

.PHONY: test-e2e
test-e2e: beets-container
	# Run e2e tests
	mkdir -p data/beets
	@docker run --rm -u `id -u`:`id -g` -w /plugin \
                -v "`pwd`:/plugin" -w /plugin \
		-v "`pwd`/data:/data" \
		-v "`pwd`/example_beets_config.yaml:/data/beets/config.yaml" \
                $(BEETS_IMG) \
		sh -c 'set -x; bats -T tests/e2e'

.PHONY: beets-sh
beets-sh: beets-container
	mkdir -p data/beets
	docker run -ti --rm -u `id -u`:`id -g` --network=host \
		-v "`pwd`:/plugin" \
		-v "`pwd`/data:/data" \
		-v "`pwd`/example_beets_config.yaml:/data/beets/config.yaml" \
		-v /run:/host/run \
		-e PULSE_SERVER=unix:/host/run/user/`id -u`/pulse/native \
		$(BEETS_IMG) sh

.PHONY: beets-container
beets-container: wheel
	docker build --rm -t $(BEETS_IMG) .

.PHONY: release
release: clean wheel
	docker run -e PYPI_USER -e PYPI_PASS -e PYPI_REPO=$(PYPI_REPO) \
		$(DOCKER_OPTS) \
		'python3 -m twine upload --repository-url "$$PYPI_REPO" -u "$$PYPI_USER" -p "$$PYPI_PASS" dist/*'

.PHONY: clean
clean:
	rm -rf build dist *.egg-info
	find . -name __pycache__ -exec rm -rf {} \; || true

.PHONY: clean-data
clean-data: clean
	rm -rf data

.PHONY: python-container
python-container:
	echo "$$DOCKERFILE" | docker build --rm -f - -t $(BUILD_IMG) .

