#! /bin/sh

# .. always start it, and always forcibly kill it :-p

case $1 in
    restart)
        killall -9 dnsmasq
        /etc/init.d/dnsmasq start
        ;;
    start)
        /etc/init.d/dnsmasq start
        ;;
    stop)
        killall -9 dnsmasq
        ;;
esac
