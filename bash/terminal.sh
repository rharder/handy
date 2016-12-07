#!/bin/bash

# Some useful things related to the terminal


INTERACTIVETERM=-YES-
if [ "$TERM" == "" ]; then INTERACTIVETERM="-NO-"; TERM="vt100"; fi
if [ "$TERM" == "dumb" ]; then INTERACTIVETERM="-NO-"; TERM="vt100"; fi
export INTERACTIVETERM

# Set up TPUT color codes
if [ "$INTERACTIVETERM" == "-YES-" ]; then
  export tReset="$(tput sgr0)"
  export tSC="$(tput sc)"
  export tRC="$(tput rc)"
  export tBold="$(tput bold)"
  export tBlack="$(tput setaf 0)"
  export tRed="$(tput setaf 1)"
  export tGreen="$(tput setaf 2)"
  export tYellow="$(tput setaf 3)"
  export tBlue="$(tput setaf 4)"
  export tPink="$(tput setaf 5)"
  export tCyan="$(tput setaf 6)"
  export tGray="$(tput setaf 8)"
  export tWhite="$(tput setaf 7)"
  export tUndOn="$(tput smul)"
  export tUndOff="$(tput rmul)"
  export tRandColor="$(tput setaf $(( $(hostname | openssl sha1 | sed 's/.*\([0-9]\).*/\1/') % 6 + 1 )) )"
else
  export tReset=
  export tSC=
  export tRC=
  export tBold=
  export tBlack=
  export tRed=
  export tGreen=
  export tYellow=
  export tBlue=
  export tPink=
  export tCyan=
  export tGray=
  export tWhite=
  export tUndOn=
  export tUndOff=
  export tRandColor=
fi


export PS1="\[${tRandColor}\]\u@\[${tBold}\]\h\[${tReset}\]:\[${tBlue}\]\w\[${tReset}\] \$ "


# File Transfer with transfer.sh
# See http://transfer.sh for details
transfer() {
	echo Uploading to transfer.sh: $1
    # write to output to tmpfile because of progress bar
    tmpfile=$( mktemp -t transferXXX )
	base=$(basename "$1")
	urlenc=$(echo $base | sed -f urlencode.sed)
    curl --progress-bar --upload-file "$1" https://transfer.sh/$urlenc >> $tmpfile;
	link=$(cat $tmpfile)
    rm -f $tmpfile;
	pushbullet -q -t "$1 uploaded: $link" -u "$link" "$link"
	echo -n $link | pbcopy
	echo "${tGreen}${link}${tReset}"
}
alias transfer=transfer



fancyconnect() { 
  if [ $# -lt 1 ]; then
    echo "USAGE: fancyconnect [command options] host"
    echo " Strips hostname off the last argument and "
    echo " prints IP information before continuing."
    echo "EXAMPLE:"
    echo " fancyconnect ssh -C joe@example.com"
  else
    HOST=${!#/[a-zA-Z0-9]*@/}
    /bin/echo -n "${tGreen}${HOST}${tReset}...${tYellow}"
    ipaddr=$(nslookup $HOST | awk '/^Non-authoritative/ {Ready=1} /^Address:/ { if ( Ready == 1 ) print $2 }')
    /bin/echo -n "${ipaddr}${tReset}...${tRed}"
    nslookup "$ipaddr" | awk '/^Non-authoritative/ {R=1} /name = / { if ( R == 1 ) print $NF }'
    /bin/echo -n "$tReset"
    $*
  fi
}


result(){
  SUCCESS=$?
  MSG=$(history 1)
  if [ $SUCCESS -eq 0 ]; then
    COLOR=$tGreen
    STATUS=Success
  else
    COLOR=$tRed
    STATUS=Fail
  fi
  echo "${COLOR}$(banner .)${tReset}"
#  growlnotify -t "Done: $STATUS" -m "$MSG"
  beep
}

# Assign a finder comment to a file
findercomment(){
  if [ $# -lt 2 ]; then
    echo "USAGE: findercomment file comment [words can continue]"
    echo "Sets the Finder comment for a file."
    echo "Example: findercomment stevejobs.jpg this one will be worth money some day"
  else
    osascript - "$@" << EOF
    on run argv
    set text item delimiters of AppleScript to " "
    set theComment to (items 2 through end of argv) as string
    set theFile to POSIX file (item 1 of argv) as alias
      tell application "Finder"
        set comment of theFile to theComment
      end tell
      return
    end run
EOF
  fi
}



