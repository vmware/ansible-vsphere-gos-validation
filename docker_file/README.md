# How to update docker image
## Build docker image
Build a new docker image with version tag vX.Y for latest release.
```
docker build . -t ansible-vsphere-gos-validation:vX.Y
```

## Run docker container to test the new docker image
```
docker run -it --privileged ansible-vsphere-gos-validation:vX.Y
```

## Tag the docker image as latest
```
docker image tag ansible-vsphere-gos-validation:vX.Y ansible-vsphere-gos-validation:latest
```
