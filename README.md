# Orbit

_Open Re-implementation of Biomedical Literature APIs_

Orbit is a framework for self-hosting clearn room re-implementations of biomedical literature APIs. The APIs that are currently supported include

 - Pubmed Entrez
 - ClinicalTrials.gov

## Live (demo) version

There are currently two versions of a live implementation running for demonstration and testing purposes:

 - production (https://orbit.health-nlp.com) for the latest stable version.
 - staging (https://orbit-staging.health-nlp.com) for the latest unstable version.

Both versions host all currently supported API re-implementations. 

For heavy API usage, please host the service yourself (see below).

## Self-host

A single docker command runs the entire data acquisition, processing, and indexing process, and starts the API.

To run all services at once, use

```
$ docker-compose -f compose.all.yml up --build
```