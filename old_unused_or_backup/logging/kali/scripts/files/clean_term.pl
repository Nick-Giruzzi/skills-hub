#!/usr/bin/perl

## Add this script to /usr/sbin/

## This script is in charge of removing special characters and obtaining a more human readable output. 

while (<>) {
    s/ \e[ #%()*+\-.\/]. | 
    \r | 
    (?:\e\[|\x9b) [ -?]* [@-~] | 
    (?:\e\]|\x9d) .*? (?:\e\\|[\a\x9c]) | 
    (?:\e[P^_]|[\x90\x9e\x9f]) .*? (?:\e\\|\x9c) | 
    \e.|[\x80-\x9f] //xg;  # Remove ASCII control sequences beginning with \e
    1 while s/[^\b][\b]//g;  # Remove all non-backspace followed by backspace
    tr/㉿/@/ds;
    s/[^@[:ascii:]]//g;
    print;
}
