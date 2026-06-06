# How to contribute

We'd love to accept your patches and contributions to this project. There are just a few small guidelines you need to follow.

## Guidelines
1. Write your patch
1. Add a test case to your patch
1. Make sure that `just test` runs properly
1. Send your patch as a PR

## Setup

1. Fork & clone the repo
1. Install [just](https://github.com/casey/just)
1. Install [Docker](https://docs.docker.com/install/)
1. Install [docker-compose](https://docs.docker.com/compose/install/)
1. Run `just test` from the root directory

`make` targets are kept for compatibility and delegate to `just`.


## How to release bumpversion itself

Execute the following commands:

    git checkout main
    git pull
    just test
    just lint
    bumpversion release
    just dist
    bumpversion --no-tag patch
    git push --tags  # Will auto publish new version to pypi by github action
