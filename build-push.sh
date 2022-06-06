#!/bin/bash

podman build -t quay.io/pbertera/pod-terminator .
podman push quay.io/pbertera/pod-terminator
