# pagespeed_exporter for providing Google PageSpeed Insights as metrics

## Requirements

Software:

    * Python3
    * APScheduler
    * requests

Google PageSpeed API key. See here on how to [get a server API key for googles platform](https://developers.google.com/console/help/generating-dev-keys).

## Configuration

The exporter is currently able to check one URI, buffer the results
and serve them as metrics.

Configuration is done via pagespeed.conf, see example file for documentation and defaults.
All config values can be overriden with environment variables given the same names.

N.B.: Google caches it's results itself for 30 seconds, so a shorter fetch interval would
be useless.
