#!/bin/bash

if [[ $(/usr/bin/id -u) -ne 0 ]]; then
    echo 'not running as root'
    exit
fi

# grab bridge-net dhcp lease
dhclient ens32

# update DNS server
echo "nameserver 8.8.8.8" > /etc/resolv.conf
