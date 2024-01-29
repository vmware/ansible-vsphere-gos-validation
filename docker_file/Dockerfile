# ansible-vsphere-gos-validation
# For users launch guest OS validation test on vSphere
# version: 3.1

# Use latest Photon OS docker image as parent image
FROM photon:latest
WORKDIR /root/ansible-vsphere-gos-validation

# Install the required packages
RUN tdnf makecache && \
    tdnf install -y python3 zip vim wget python3-pip \
    sshpass gawk nfs-utils iana-etc python3-lxml python3-setuptools \
    python3-wheel  python3-jmespath python3-netaddr && \
    pip3 install pycdlib pywinrm pyvmomi pypsrp passlib

# Install ansible-core
RUN pip3 install ansible-core==2.15.8

# Install Ansible collections
# You can set https proxy if collections are failed to install from Galaxy server, e.g.,
# ENV HTTPS_PROXY="https://proxy.xxxx.com:xxxx"
# Ansible 2.14.0 or later requires the locale encoding to be UTF-8
ENV LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
COPY requirements.yml /tmp/requirements.yml
RUN ansible-galaxy install -r /tmp/requirements.yml

# Download latest 'ansible-vsphere-gos-validation' release to working dir
RUN curl -s https://api.github.com/repos/vmware/ansible-vsphere-gos-validation/releases/latest | grep "tarball_url" | cut -d "\"" -f 4 | xargs -n 1 wget -O test.tar.gz && \
    tar -zxf test.tar.gz && \
    mv vmware-ansible-vsphere-gos-validation*/* ./

# Clean up unused files
RUN rm -rf test.tar.gz vmware-ansible-vsphere-gos-validation* && \
    tdnf clean all && \
    rm -rf /var/cache/* /root/.cache/pip/* /var/log/* /tmp/* /root/.ansible/tmp/*

# Known issue: ping: socket SOCK_DGRAM 1: Permission denied, Kernel bug workaround
CMD echo 0 99999999 | tee /proc/sys/net/ipv4/ping_group_range && \
    /bin/bash
