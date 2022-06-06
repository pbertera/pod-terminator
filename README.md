# Pod Terminator

## Usage

Kill all the pods with the `metadata.deletionTimestamp` older than `MAX_SECONDS` env variable

```
$ MAX_SECONDS=3 python ./terminator.py
```

### Container image

With OAuth authentication (OpenShift 4.x only)

```
$ podman run -it -e CYCLE_DELAY=3 -e API=https://api.ocp4.example.com:6443 -e USERNAME=admin -e PASSWORD=passwd -e DRY_RUN=yes -e MAX_SECONDS=30 quay.io/pbertera/pod-terminator
```

With Kubeconfig

```
$ podman run -it v ${PWD}/kubeconfig:/kubeconfig:z -e KUBECONFIG=/kubeconfig -e MAX_SECONDS=30 quay.io/pbertera/pod-terminator
```

## Authentication

By if the `USERNAME` env. variable is not deinfed the script looks for the `KUBECONFIG` env. variable or tries to load the `~/.kube/config` file.

Together with `USERNAME` also `API` and `PASSWORD` must be defined. User-Password authentication works on OCP 4.x only.

## Configuration

Supported environment variables

* `API` the Kubernetes API URL with the proper schema and port
* `USERNAME` the OAuth username
* `PASSWORD` the OAuth password
* `MAX_SECONDS` the treshold to use when killing the pod
* `CYCLE_DELAY` the delay between each cycle
* `DRY_RUN` do nothing, just log the pod name
