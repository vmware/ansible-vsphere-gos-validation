# How to update docker image
## Build docker image
Build a new docker image with version tag vX.Y for latest release.
```
cp -f ../requirements.yml .
docker build . -t projects.registry.vmware.com/gos_cert/ansible-vsphere-gos-validation:vX.Y
```

## Run docker container to test the new docker image
```
docker run -it --privileged projects.registry.vmware.com/gos_cert/ansible-vsphere-gos-validation:vX.Y
```

## Push new docker image to registry
```
docker login projects.registry.vmware.com
docker push projects.registry.vmware.com/gos_cert/ansible-vsphere-gos-validation:vX.Y
```

## Tag the docker image as latest one and push it
```
docker image tag projects.registry.vmware.com/gos_cert/ansible-vsphere-gos-validation:vX.Y projects.registry.vmware.com/gos_cert/ansible-vsphere-gos-validation:latest
docker login projects.registry.vmware.com
docker push projects.registry.vmware.com/gos_cert/ansible-vsphere-gos-validation:latest
```
