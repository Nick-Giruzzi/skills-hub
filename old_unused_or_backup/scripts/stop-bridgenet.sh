#!/bin/bash

if [[ $(/usr/bin/id -u) -ne 0 ]]; then
    echo 'not running as root'
    exit
fi

# grab bridge-net dhcp lease
ip link set ens32 down
ip link set ens32 up

# update DNS server
echo "nameserver 127.0.0.1" > /etc/resolv.conf
echo "nameserver 10.0.0.1" >> /etc/resolv.conf
