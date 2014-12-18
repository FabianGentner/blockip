Permissions
===========

*blockip* uses LDAP to manage user authorizations for access to its resources. The following LDAP roles are used:

*reader*
    Allows the user to see the black- and whitelist. Implied by all other roles.

*history-reader*
    Allows the user to see inactive black- and whitelist entries. Implies *reader*.

*blacklister*
    Allows the user to add single IP addresses -- but not networks -- to the blacklist. Implies *reader*, and is
    implied by *network-blacklister*.

*network-blacklister*
    Allows the user to add networks to the blacklist. Implies *reader* and *blacklister*.

*unblacklister*
    Allows the user to remove single IP addresses -- but not networks -- from the blacklist. Implies *reader* and is
    implied by *network-unblacklister*.

*network-unblacklister*
    Allows the user to remove networks from the blacklist. Implies *reader* and *unblacklister*.

*whitelister*
    Allows the user to add single IP addresses -- but not networks -- to the whitelist. Implies *reader*, and is
    implied by *network-whitelister*.

*network-whitelister*
    Allows the user to add networks to the whitelist. Implies *reader* and *whitelister*.

*unwhitelister*
    Allows the user to remove single IP addresses -- but not networks -- from the whitelist. Implies *reader* and is
    implied by *network-unwhitelister*.

*network-unwhitelister*
    Allows the user to remove networks from the whitelist. Implies *reader* and *unwhitelister*.


Authentication
--------------

To authenticate a user, *blockip* connects to LDAP with the credentials the user provided to log in to *blockip*.
It then searches LDAP for *blockip* roles that list the user as a member. Authentication data is cached in memory
for ten minutes.

The exact behavior can be customized using the configuration settings ``host``, ``use_ssl``, ``user_name_template``,
``role_search_base``, and ``role_search_filter_template`` from the ``ldap`` section of the configuration file.

Suppose the configuration file reads, in part,

.. code::

    [ldap]
    host=ldaps://ldap.yourcompany.com
    use_ssl=true
    user_name_template=uid={user_name},ou=users,dc=yourcompany,dc=com
    role_search_base=ou=blockip,ou=services,dc=yourcompany,dc=com
    role_search_filter_template=(member=uid={user_name},ou=users,dc=yourcompany,dc=com)

If a user provides the user name and password "jdoe" and "letmein", respectively, *blockip* would attempt to log in to
the LDAP instance at ldaps://ldap.yourcompany.com with the user name "uid=jdoe,ou=users,dc=yourcompany,dc=com" and the
password "letmein". It would then search for entries matching ``(member=uid=jdoe,ou=users,dc=yourcompany,dc=com)`` in
the subtree rooted at `ou=blockip,ou=services,dc=yourcompany,dc=com`. The common names of the entries found would form
the set of the user's roles.

