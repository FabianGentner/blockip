Blacklist vs. Whitelist
=======================

*blockip* allows users both to blacklist and to whitelist IP addresses. The interaction between blacklist and whitelist
bears some explanation.

A given IP address is blocked if and only if it is blacklisted.

A given IP address that is neither blacklisted nor whitelisted is not blocked.

If an IP address is whitelisted, it cannot be blacklisted (and vice versa). That is, the whitelist serves as a safety
mechanism that prevents IP addresses that must not be blacklisted for one reason or another from being blacklisted by
accident. Only the system team should be able to add IP addresses to the whitelist or remove them from it, so most
users' only contact with the whitelist will be *blockip* citing some whitelist entry when it prevents them from making
a terrible mistake by blacklisting the wrong address.



