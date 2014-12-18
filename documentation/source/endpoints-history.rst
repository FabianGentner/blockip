``/history`` Endpoints
======================

*blockip* provides the following endpoint for accessing historical black- and whitelist data:


.. http:get:: /history/(address)

    Lists all active and inactive black- and whitelist entries that overlap the given IP address (or block of IP addresses).

    :param address:
        The IP address (or block of IP addresses) historical black- and whitelist entries should be listed for.

    :status 401: If the user is not logged in.
    :status 403: If the user lacks the role *history-reader*.
    :status 200: Otherwise.


Examples
--------

An example for using the ``/history`` endpoint with ``curl`` follows. To enhance readability, the examples
add a trailing newline to the output from ``curl``, omit some less relevant output, and use the environment variables
``HOST`` and ``USER`` in the commands instead of distracting sample values.

.. literalinclude:: ../../test-scenarios/scenarios/history/all.txt
    :language: sh

