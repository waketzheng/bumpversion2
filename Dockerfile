FROM themattrix/tox-base

RUN apt-get update && apt-get install -y git-core mercurial

# Update pyenv for access to newer Python releases.
RUN cd /.pyenv \
    && git fetch \
    && git checkout v2.4.2

# only install certain versions for tox to use
RUN pyenv versions
RUN pyenv global system 3.9.19 3.10.14 3.11.9 3.12.3

RUN git config --global user.email "bumpversion_test@example.org"
RUN git config --global user.name "Bumpversion Test"

ENV PYTHONDONTWRITEBYTECODE = 1  # prevent *.pyc files

WORKDIR /code
COPY . .
CMD tox
