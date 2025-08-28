# locust-asserter

Main purpose of this library is to provide a convenient way to make assertions in
performance tests written in [Locust framework](https://docs.locust.io/en/stable/index.html)

## Table of contents

- [Where to find locust-asserter](#where-to-find-locust-asserter)
- [Installation](#installation)
    + [Installation by pip](#installation-by-pip)
    + [Installation by uv using pyproject.toml](#installation-by-uv-using-pyprojecttoml)
- [Usage example](#usage-example)
    + [Possible stats to use in assertions](#possible-stats-to-use-in-assertions)
    + [Possible operators](#possible-operators)
    + [Total stats](#total-stats)
    + [Endpoint stats](#endpoint-stats)
      - [HTTP methods](#http-methods)
      - [Custom methods](#custom-methods)
    + [Example](#example)
- [Pre-commit](#pre-commit)
- [FAQ](#faq)
    + [Error: No data gathered from locust stats](#error-no-data-gathered-from-locust-stats)
- [Author](#author)

## Where to find locust-asserter

The package can be found inside fork of [locust](https://github.com/locustio/locust) repository: [kosiecg/locust](https://github.com/kosiecg/locust) on branch [add-locust-asserter](https://github.com/kosiecg/locust/tree/add-locust-asserter)

The exact package location is: [locust/locust/contrib/locust-asserter](https://github.com/kosiecg/locust/tree/add-locust-asserter/locust/contrib/locust-asserter)

## Installation

First you need to clone fork of locust repository [kosiecg/locust](https://github.com/kosiecg/locust) on branch [add-locust-asserter](https://github.com/kosiecg/locust/tree/add-locust-asserter) 

### Installation by pip
As a prerequisite see: [Installation](#installation)

```bash
python -m pip install --editable <your path to cloned repository>/locust/locust/contrib/locust-asserter
```

### Installation by uv using pyproject.toml
As a prerequisite see: [Installation](#installation)


```
[project]
requires-python = ">=3.11"
dependencies = [
    "locust >= 2.34.0",
    "gevent == 24.11.1; sys_platform == 'win32'", # Currently for Windows newer versions are not working
    "locust-asserter == 1.5.0"
]
[tool.uv.sources]
locust-asserter = { path = "<your path to cloned repository>/locust/locust/contrib/locust-asserter", editable = true }
```

and then command `uv run` can be used

## Usage example

> [!important]
> How to write and run Locust test check [Locust framework](https://docs.locust.io/en/stable/index.html)

### Possible stats to use in assertions

- `fail_ratio` failed_requests / requests_number ( fail_ratio + success_ratio = 1 )
- `success_ratio` success_requests / requests_number ( fail_ratio + success_ratio = 1 )
- `failures_per_second`
- `requests_per_second`
- `failures_number`
- `requests_number`
- `response_time` category:
    + `response_time.percentile(<given_percentile>)` e.g. `response_time.percentile(90)`
    + `response_time.maximum`
    + `response_time.minimum`
    + `response_time.average`
    + `response_time.median`

### Possible operators

- `eq` equal
- `gt` greater than
- `lt` less than

### Total stats

For making assertions regarding `total` stats gathered by locust during tests.

```python
from locust_asserter import LocustAsserter

asserter = LocustAsserter()

asserter.total.fail_ratio.lt(0.2)  # The same as: asserter.total.success_ratio.gt(0.8)

asserter.total.failures_per_second.lt(1)
asserter.total.requests_per_second.gt(20)

asserter.total.failures_number.lt(10)
asserter.total.requests_number.gt(300)

asserter.total.response_time.percentile(90).lt(500)
asserter.total.response_time.maximum.lt(1000)
asserter.total.response_time.minimum.lt(100)
asserter.total.response_time.average.lt(300)
asserter.total.response_time.median.lt(300)
```

### Endpoint stats

#### HTTP methods
If `method` used as a part of combination `(endpoint, method)` is one of:
- GET
- POST
- PUT
- PATCH
- DELETE
- HEAD
- OPTIONS
- TRACE
- CONNECT

then no warning in LocustAsserter is displayed.

#### Custom methods
If `method` used as a part of combination `(endpoint, method)` is custom i.e., not one of
[HTTP methods](#http-methods), then warning is displayed as a precautionary measure.

For example
```console
------------------------------------------------------- Warnings -------------------------------------------------------


Added assertion for endpoint='message_processing' with custom method='KafkaP'.
In case of problems check carefully method name.


------------------------------------------------------- Warnings -------------------------------------------------------
```
<br><br>

Endpoint stats are used for making assertions regarding stats for specific combination `(endpoint, method)`
gathered by locust during tests.

When writing test in locust and making a request like below:

```python
from locust import task


@task
def get_health(self):
    with self.client.get(url="/health"):
        pass
```

you should use `url` parameter name in assertions for combination (endpoint, method) e.g.
`asserter.details("/health", "GET").response_time.percentile(95).lt(600)`

<br><br>
**However, when `name` parameter is used it's always taking precedence over `url`**

```python
from locust import task


@task
def get_health(self):
    with self.client.get(url="/health", name="health_endpoint"):
        pass
```

and you should make an assertion e.g
`asserter.details("health_endpoint", "GET").response_time.percentile(95).lt(600)`

> [!warning]
> You cannot use `url` parameter name in endpoint assertions when `name` was specified for this endpoint

### Example

```python
from locust_asserter import LocustAsserter

asserter = LocustAsserter()

asserter.total.fail_ratio.lt(0.2)  # The same as: asserter.total.success_ratio.gt(0.8)

asserter.total.failures_per_second.lt(1)
asserter.total.requests_per_second.gt(20)

asserter.total.failures_number.lt(10)
asserter.total.requests_number.gt(300)

asserter.total.response_time.percentile(90).lt(500)
asserter.total.response_time.maximum.lt(1000)
asserter.total.response_time.minimum.lt(100)
asserter.total.response_time.average.lt(300)
asserter.total.response_time.median.lt(300)

# The same as: asserter.details("health_endpoint", "GET").success_ratio.gt(0.9)
asserter.details("health_endpoint", "GET").fail_ratio.lt(0.1)

asserter.details("health_endpoint", "GET").response_time.percentile(95).lt(600)
asserter.details("health_endpoint", "GET").requests_per_second.gt(5)
asserter.details("health_endpoint", "GET").requests_number.gt(200)
```

## Pre-commit

To install pre-commit before developing locust-asserter simply run inside the shell:
```bash
pre-commit install
```

## FAQ

### Error: No data gathered from locust stats

There are several possibilities causing this error:

1. Error in assertion definition
    - Using `url` parameter name in endpoint assertion when `name` was specified for this endpoint
      [Check: Endpoint stats](#endpoint-stats)

    - Typo in the endpoint name or using different method ([HTTP](#http-methods) or [custom](#custom-methods)) that was called in the test
      <br><br>
2. 'Locust' framework not gathered any stats for the endpoint
   [Check: Locust Documentation](https://docs.locust.io/en/stable/index.html) \
   It can occur due to several reasons like:
    - Incorrect locust task definition in the test
    - Incorrect tasks' weights definition (often connected with too short test time)
    - etc.


## Author

- [Grzegorz Kosiec](https://github.com/kosiecg)
