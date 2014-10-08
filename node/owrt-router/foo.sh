# Set up manually keyed IPsec without too much pain (cough)
pad0 () {
    LEN=$1 ; shift
    LEN=$((LEN-1)) 
    # Due to how we iterate, must use len-1
    DATA="$*"
    echo -n "$DATA"
    for t in $(seq ${#DATA} $LEN)
    do
        echo -n "0"
    done
}

str2hex () {
    DATA="$*"
    DLEN=${#DATA}
    DLEN=$((DLEN-1))
    for i in $(seq 0 $DLEN)
    do
        printf "%02X" \""${DATA:$i:1}"
    done
}

x () {
    echo "#$*"
    $*
}

echo $(pad0 4 foo)
echo $(pad0 3 foo)
echo $(pad0 32 $(str2hex foo))

SPI=0x42
PASSWORD=foo

AUTHALG='md5'
AUTHKEYLEN=32

ENCALG='aes'
ENCKEYLEN=32

#ENCALG='des3_ede'
#ENCKEYLEN=48

REQID=42

HNCP_PORT=8808
BABEL_PORT=6696

# if want to prevent unauthorized non-linklocal traffic too
PROTECT_NETS="::/0"

# if want to secure only linklocal IPv6
# (Note: Only on per-port basis!)
PROTECT_NETS="fe80::/64 ff02::/16" # does not. gnn.

PROTECT_PORTS="$HNCP_PORT $BABEL_PORT"
#PROTECT_PORTS="$HNCP_PORT"

# Clear old state with our reqid
x ip xfrm state deleteall reqid $REQID

# Clear old policies
#x ip xfrm policy deleteall reqid $REQID
# .. sigh.. wish this was possible :p
x ip xfrm policy deleteall 

# State - one SA is all you need(?)
x ip xfrm state add \
    dst :: \
    spi $SPI \
    proto esp reqid $REQID \
    auth $AUTHALG 0x$(pad0 $AUTHKEYLEN $(str2hex "$PASSWORD")) \
    enc $ENCALG 0x$(pad0 $ENCKEYLEN $(str2hex "$PASSWORD")) 

# Policy - per-network..
for DST in $(echo $PROTECT_NETS)
do
    # Inbound - accept IPsec
    x ip xfrm policy add dst $DST proto esp dir in priority 1 tmpl reqid $REQID 
    for DSTPORT in $(echo $PROTECT_PORTS)
    do
        # Non-encrypted isn't ok
        #x ip xfrm policy add \
        #    dst $DST proto udp dport $DSTPORT dir in priority 2 action block

        # Encrypt outgoing, mandatory
        x ip xfrm policy add \
            dst $DST proto udp dport $DSTPORT dir out \
            tmpl reqid $REQID proto esp
    done
done
x ip xfrm state
x ip xfrm policy

