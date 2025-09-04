#!/bin/bash
#
# Challenge Sever
# Copyright 2024 Carnegie Mellon University.
# NO WARRANTY. THIS CARNEGIE MELLON UNIVERSITY AND SOFTWARE ENGINEERING INSTITUTE MATERIAL IS FURNISHED ON AN "AS-IS" BASIS. CARNEGIE MELLON UNIVERSITY MAKES NO WARRANTIES OF ANY KIND, EITHER EXPRESSED OR IMPLIED, AS TO ANY MATTER INCLUDING, BUT NOT LIMITED TO, WARRANTY OF FITNESS FOR PURPOSE OR MERCHANTABILITY, EXCLUSIVITY, OR RESULTS OBTAINED FROM USE OF THE MATERIAL. CARNEGIE MELLON UNIVERSITY DOES NOT MAKE ANY WARRANTY OF ANY KIND WITH RESPECT TO FREEDOM FROM PATENT, TRADEMARK, OR COPYRIGHT INFRINGEMENT.
# Licensed under a MIT (SEI)-style license, please see license.txt or contact permission@sei.cmu.edu for full terms.
# [DISTRIBUTION STATEMENT A] This material has been approved for public release and unlimited distribution.  Please see Copyright notice for non-US Government use and distribution.
# DM24-0645
#


## This script is being run instead of the actual shell. 
## It makes sure that every shell is running with the script command and the session is being recorded.
## This script is only recording sessions started with xfce4-terminal. It doesn't record terminals such as: qterminal, gnome-terminal, xterm or others...


if [ -z "$UNDER_SCRIPT" ] ; then
    export UNDER_SCRIPT=1
    export DEFAULT_LOG_PREFIX="/tmp/"
    export PLAIN_LOG_PREFIX="/tmp/"
    export ONELINE_LOG_PREFIX="/tmp/"
    touch $DEFAULT_LOG_PREFIX/$$-script.log
    touch $PLAIN_LOG_PREFIX/$$-script-plain.log
    touch $ONELINE_LOG_PREFIX/$$-script-oneline.log
    tail -f "$DEFAULT_LOG_PREFIX"/$$-script.log | while read line0; do echo $line0 | clean_term.pl >> "$PLAIN_LOG_PREFIX"/$$-script-plain.log ; done &
    linenum=0
    tail -f "$PLAIN_LOG_PREFIX"/$$-script-plain.log | while read line1; do
    ((linenum++))
        if [[ -z $line1 ]]; then
            continue
        else
            if [[ $linenum -eq 1 ]]; then
                echo "$line1" >> "$ONELINE_LOG_PREFIX"/$$-script-oneline.log;
                continue
            elif [[ $line1 == *"@$(hostname)"* ]]; then
                echo -e "\n"  >> "$ONELINE_LOG_PREFIX"/$$-script-oneline.log;
                echo -n "$line1 ----- " >> "$ONELINE_LOG_PREFIX"/$$-script-oneline.log;
                continue
            elif [[ $line1 == \$* || $line1 == \#* ]]; then
                echo -n "$line1 ----- " >> "$ONELINE_LOG_PREFIX"/$$-script-oneline.log;
                continue
            else
                echo -n $line1 | awk '{printf "%s\\n", $0}' >> "$ONELINE_LOG_PREFIX"/$$-script-oneline.log;
                continue
            fi
        fi
    done &
    script -q -f $DEFAULT_LOG_PREFIX/$$-script.log
    exit
fi
