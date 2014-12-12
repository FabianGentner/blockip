``/blacklist`` Endpoints
========================

*blockip* provides the following endpoints for managing blacklists:


.. http:get:: /blacklist

    Lists all active blacklist entries.

    :status 401: If the user is not logged in.
    :status 403: If the user lacks the role `apps/blockip/reader`.
    :status 200: Otherwise.


.. http:get:: /blacklist/(address)

    Lists all active blacklist entries that overlap the given IP address (or block of IP addresses).

    :param address:
        The IP address (or block of IP addresses) blacklist entries should be listed for.

    :status 401: If the user is not logged in.
    :status 403: If the user lacks the role `apps/blockip/reader`.
    :status 200: Otherwise.


.. http:post:: /blacklist/(address)

    Adds the given IP address (or block of IP addresses) to the blacklist.

    It is possible for overlapping blocks of IP addresses to be blacklisted. That is, 192.0.2.0/30 being blacklisted
    does not prevent 192.0.2.0/24 or 192.0.2.1 from being blacklisted as well. The response lists any such overlapping
    entries as `overlapping_blacklist_entries`.

    Blacklisting an IP address when that exact IP address is already blacklisted supersedes the existing blacklist
    entry if the new duration is longer than the old one. That is, if 192.0.2.1 is blacklisted for another two hours,
    blacklisting it for eight hours, will result in that address being blacklisted for eight hours. If the new duration
    is shorter than the duration of the existing blacklist entry, the operation has no effect, but is not considered
    to be in error.

    Attempting to blacklist an IP address that is whitelisted results in an error.

    :param address:
        The IP address (or block of IP addresses) that should be added to the blacklist.
    :form comment:
        A comment describing the reason the address should be blacklisted. Required.
    :form for:
        The time span for which the IP address should be blacklisted. See `Block Duration`_ for details.
    :form until:
        The date and time until which the IP address should be blacklisted. See `Block Duration`_ for details.

    :status 401: If the user is not logged in.
    :status 403: If the user lacks the role `apps/blockip/blacklister`, or `apps/blockip/network-blacklister` if the
                 request was to blacklist a block of IP addresses.
    :status 400: If the IP address or duration is malformed, or the comment is missing.
    :status 409: If blacklisting the IP address would conflict with a whitelisted IP address.
    :status 200: If nothing has been done because the exact IP address was already blacklist for a greater duration.
    :status 201: If the IP address has been successfully blacklisted.


.. http:delete:: /blacklist/(address)

    Removes the given IP address (or block of IP addresses) from the blacklist (or rather, marks it as canceled).

    *Important:* If there were multiple overlapping blacklist entries, the IP address or a subset of the IP addresses
    that make up a block of IP addresses may still be blacklisted. For example, if both 192.0.2.0/24 and 192.0.2.1 are
    blacklisted, removing 192.0.2.1 from the blacklist will have no real effect since that address is part of
    192.0.2.0/24, which will still be blacklisted. Conversely, removing 192.0.2.0/24 from the blacklist will leave
    192.0.2.1 on the blacklist. The response lists any such overlapping entries as `overlapping_blacklist_entries`.

    Attempting to remove an IP address from the blacklist when that exact IP address is not actually blacklisted has
    has no effect, but is not considered an error.

    :param address:
        The IP address (or block of IP addresses) that should be removed to the blacklist.
    :form comment:
        A comment describing the reason the address should no longer be blacklisted. Required.

    :status 401: If the user is not logged in.
    :status 403: If the user lacks the role `apps/blockip/unblacklister`, or `apps/blockip/network-unblacklister` if the
                 request was to remove a block of IP addresses from the blackelist.
    :status 400: If the IP address is malformed or the comment is missing.
    :status 200: If the IP address has been successfully removed from the blacklist or wasn't actually on the
                 blacklist.

Block Duration
--------------

When adding an IP address to the blacklist, the duration of the block can be specified using either the form parameter
`for` or the form parameter `until`. The parameter `for` specifies the duration as a time span starting at the time the
request is processed. (That is, a value of :samp:`8 hours` would result in a block that remains in effect for eight
hours.) The parameter `until` specifies the duration by its end as a date and time. (That is, a value of
:samp:`2014-11-14 16:00:00` would result in a block that remains in effect until 16:00 UTC on November 14, 2014.)

For determining whether a block is in effect, the time of the database server (as determined using ``now() at time zone
'utc'``) is used.

Legal values for `for` are all strings that PostgreSQL can parse as an interval with a (positive) length of at least
one minute. Examples include :samp:`8h`, :samp:`1 day`, :samp:`2.5w`, :samp:`1 year 1 day`, and :samp:`P1Y2M3DT4H5M6S`.

Legal values for `until` are all strings that PostgreSQL can parse as a timestamp with time zone that lies at least one
minute in the future. Examples include :samp:`2014-11-14 16:03:00`, :samp:`2014-11-14 17:03:00+01:00`,
:samp:`2014-11-14 17:03:00 CET`, and :samp:`November 14, 2014 AD, at 17:03:00 (Europe/Berlin)` (except that those will
be in the past by the time you read this). Values without a time zone are assumed to be UTC, and values with a time
zone are converted to UTC.

If neither `for` nor `until` are given, `for` defaults to :samp:`8 hours`. If both are given, an error is raised.


Examples
--------

A number of examples for using the ``/blacklist`` endpoints with ``curl`` follow. To enhance readability, the examples
add a trailing newline to the output from ``curl``, omit some less relevant output, and use the environment variables
``HOST`` and ``USER`` in the commands instead of distracting sample values.


Blacklisting an IP Address
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. literalinclude:: ../../test-scenarios/scenarios/blacklist/add.txt
    :language: sh


Special Case: Blacklisting a Whitelisted IP Addresses
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Attempting to blacklist an IP address that is whitelisted results in an error:

.. literalinclude:: ../../test-scenarios/scenarios/blacklist/whitelisted/exact.txt
    :language: sh


Special Case: Blacklisting Overlapping IP Addresses
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

It is possible for overlapping blocks of IP addresses to be blacklisted, regardless of the duration of the individual
blacklist entries:

.. literalinclude:: ../../test-scenarios/scenarios/blacklist/overlapping/medium.txt
    :language: sh


Superseding an Existing Blacklist Entry
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Creating a new blacklist entry that has a longer duration than an existing entry for the same exact IP address
supersedes the existing entry:

.. literalinclude:: ../../test-scenarios/scenarios/blacklist/existing/longer.txt
    :language: sh


Special Case: Existing Blacklist Entry Is Not Superseded
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Creating a new blacklist entry that has a shorter duration than an existing entry for the same exact IP address
does *not* supersede the existing entry:

.. literalinclude:: ../../test-scenarios/scenarios/blacklist/existing/shorter.txt
    :language: sh


Removing an IP Address from the Blacklist
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. literalinclude:: ../../test-scenarios/scenarios/unblacklist/simple.txt
    :language: sh


Special Case: Removing Overlapping IP Addresses from the Blacklist
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When removing an IP address from the blacklist, any overlapping IP addresses that are still on the blacklist are
reported in the response:

.. literalinclude:: ../../test-scenarios/scenarios/unblacklist/overlapping/medium.txt
    :language: sh


Special Case: Removing a Non-Blacklisted IP Addresses from the Blacklist
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Attempting to remove an IP address that is not actually blacklisted from the blacklist is not an error:

.. literalinclude:: ../../test-scenarios/scenarios/unblacklist/not-blacklisted.txt
    :language: sh



