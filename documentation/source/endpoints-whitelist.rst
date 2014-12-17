``/whitelist`` Endpoints
========================

*blockip* provides the following endpoints for managing whitelists:


.. http:get:: /whitelist

    Lists all active whitelist entries.

    :status 401: If the user is not logged in.
    :status 403: If the user lacks the role *reader*.
    :status 200: Otherwise.


.. http:get:: /whitelist/(address)

    Lists all active whitelist entries that overlap the given IP address (or block of IP addresses).

    :param address:
        The IP address (or block of IP addresses) whitelist entries should be listed for.

    :status 401: If the user is not logged in.
    :status 403: If the user lacks the role *reader*.
    :status 200: Otherwise.


.. http:post:: /whitelist/(address)

    Adds the given IP address (or block of IP addresses) to the whitelist.

    It is possible for overlapping blocks of IP addresses to be whitelisted. That is, 192.0.2.0/30 being whitelisted
    does not prevent 192.0.2.0/24 or 192.0.2.1 from being whitelisted as well. The response lists any such overlapping
    entries as `overlapping_whitelist_entries`.

    Attempting to add an IP address to the whitelist when that exact IP address is already whitelisted has no effect,
    but is not considered an error.

    Attempting to whitelist an IP address that is blacklisted results in an error.

    :param address:
        The IP address (or block of IP addresses) that should be added to the whitelist.
    :form comment:
        A comment describing the reason the address should be whitelisted. Required.

    :status 401: If the user is not logged in.
    :status 403: If the user lacks the role *whitelister*, or *network-whitelister* if the
                 request was to whitelist a block of IP addresses.
    :status 400: If the IP address is malformed or the comment is missing.
    :status 409: If whitelisting the IP address would conflict with a blacklisted IP address.
    :status 200: If nothing has been done because the exact IP address was already whitelisted.
    :status 201: If the IP address has been successfully whitelisted.


.. http:delete:: /whitelist/(address)

    Removes the given IP address (or block of IP addresses) from the whitelist (or rather, marks it as canceled).

    *Important:* If there were multiple overlapping whitelist entries, the IP address or a subset of the IP addresses
    that make up a block of IP addresses may still be whitelisted. For example, if both 192.0.2.0/24 and 192.0.2.1 are
    whitelisted, removing 192.0.2.1 from the whitelist will have no real effect since that address is part of
    192.0.2.0/24, which will still be whitelisted. Conversely, removing 192.0.2.0/24 from the whitelist will leave
    192.0.2.1 on the whitelist. The response lists any such overlapping entries as `overlapping_whitelist_entries`.

    Attempting to remove an IP address from the whitelist when that exact IP address is not actually whitelisted has
    has no effect, but is not considered an error.

    :param address:
        The IP address (or block of IP addresses) that should be removed to the whitelist.
    :form comment:
        A comment describing the reason the address should no longer be whitelisted. Required.

    :status 401: If the user is not logged in.
    :status 403: If the user lacks the role *unwhitelister*, or *network-unwhitelister* if the
                 request was to remove a block of IP addresses from the whitelist.
    :status 400: If the IP address is malformed or the comment is missing.
    :status 200: If the IP address has been successfully removed from the whitelist or wasn't actually on the
                 whitelist.


Examples
--------

A number of examples for using the ``/whitelist`` endpoints with ``curl`` follow. To enhance readability, the examples
add a trailing newline to the output from ``curl``, omit some less relevant output, and use the environment variables
``HOST`` and ``USER`` in the commands instead of distracting sample values.


Whitelisting an IP Address
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. literalinclude:: ../../test-scenarios/scenarios/whitelist/add.txt
    :language: sh


Special Case: Whitelisting a Blacklisted IP Addresses
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Attempting to whitelist an IP address that is blacklisted results in an error:

.. literalinclude:: ../../test-scenarios/scenarios/whitelist/blacklisted/exact.txt
    :language: sh


Special Case: Whitelisting Overlapping IP Addresses
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

It is possible for overlapping blocks of IP addresses to be whitelisted.

.. literalinclude:: ../../test-scenarios/scenarios/whitelist/overlapping/medium.txt
    :language: sh


Whitelisting an IP Address Twice
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Attempting to whitelist an IP address when that exact IP address is already whitelisted has no effect, but is not
considered an error.

.. literalinclude:: ../../test-scenarios/scenarios/whitelist/add-twice.txt
    :language: sh


Removing an IP Address From the Whitelist
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. literalinclude:: ../../test-scenarios/scenarios/unwhitelist/simple.txt
    :language: sh


Special Case: Removing Overlapping IP Addresses From the Whitelist
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When removing an IP address from the whitelist, any overlapping IP addresses that are still on the whitelist are
reported in the response:

.. literalinclude:: ../../test-scenarios/scenarios/unwhitelist/overlapping/medium.txt
    :language: sh


Special Case: Removing a Non-Whitelisted IP Addresses from the Whitelist
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Attempting to remove an IP address that is not actually whitelisted from the whitelist is not an error:

.. literalinclude:: ../../test-scenarios/scenarios/unwhitelist/not-whitelisted.txt
    :language: sh

