#!/bin/bash 
#
# Challenge Sever
# Copyright 2024 Carnegie Mellon University.
# NO WARRANTY. THIS CARNEGIE MELLON UNIVERSITY AND SOFTWARE ENGINEERING INSTITUTE MATERIAL IS FURNISHED ON AN "AS-IS" BASIS. CARNEGIE MELLON UNIVERSITY MAKES NO WARRANTIES OF ANY KIND, EITHER EXPRESSED OR IMPLIED, AS TO ANY MATTER INCLUDING, BUT NOT LIMITED TO, WARRANTY OF FITNESS FOR PURPOSE OR MERCHANTABILITY, EXCLUSIVITY, OR RESULTS OBTAINED FROM USE OF THE MATERIAL. CARNEGIE MELLON UNIVERSITY DOES NOT MAKE ANY WARRANTY OF ANY KIND WITH RESPECT TO FREEDOM FROM PATENT, TRADEMARK, OR COPYRIGHT INFRINGEMENT.
# Licensed under a MIT (SEI)-style license, please see license.txt or contact permission@sei.cmu.edu for full terms.
# [DISTRIBUTION STATEMENT A] This material has been approved for public release and unlimited distribution.  Please see Copyright notice for non-US Government use and distribution.
# DM24-0645
#


files_path=/home/user/Desktop/scripts/files

## Create needed directories
mkdir -p /etc/xdg/xfce4/terminal/

## Copy files to directories
cp $files_path/script.sh /usr/sbin/
cp $files_path/clean_term.pl /usr/sbin/
cp $files_path/terminalrc /etc/xdg/xfce4/terminal/


## Change files/directories ownership
chown user:user /usr/sbin/script.sh
chown user:user /usr/sbin/clean_term.pl
chown user:user /etc/xdg/xfce4/terminal/terminalrc

## Give proper permissions to scripts
chmod +x /usr/sbin/script.sh
chmod +x /usr/sbin/clean_term.pl

## Terminal Logging - Install xfce-4-terminal and dconf
apt install xfce4-terminal -y 
apt install dconf-cli -y

## Terminal Logging - Change Terminal Emulator from qterminal to xfce4-terminal
sed -i 's/TerminalEmulator=qterminal/TerminalEmulator=xfce4-terminal/g' /etc/xdg/xfce4/helpers.rc

## Terminal Logging - Remove all other terminals provided
apt remove xterm -y && apt remove qterminal -y && apt remove gnome-terminal -y

## Terminal Logging - Change shell from zsh to bash. Then, remove zsh
chsh -s /bin/bash root
chsh -s /bin/bash user
apt remove zsh
