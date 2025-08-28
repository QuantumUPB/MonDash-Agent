# MonDash Agent

<p float="left">
    <img src="upb.png" alt="University Politehnica of Bucharest" width="50"/>
    <img src="Logo.png" alt="Quantum Team @ UPB" width="100"/>
</p>

MonDash periodically polls a set of key management nodes and prints their
aggregated status as JSON. Endpoints and node information are defined in a YAML
configuration file. Each node's availability is queried from
`<base_url>/nodes/<name>/status`.

## Configuration

Create a `config.yaml` file listing node names, their URLs and the consumers
to monitor. SAE identifiers are automatically generated using the format
`<node>-<consumer>`.

```yaml
names:
  - campus
  - precis
  - rectorat
urls:
  campus: http://localhost:8000
  precis: http://localhost:8001
  rectorat: http://localhost:8002
consumers:
  - fileTransfer1
  - vault1
```

The path to this file can be overridden using the `CONFIG_FILE` environment
variable. Polling interval is controlled by `POLL_INTERVAL` (default: 60 seconds).

Set `POST_RESULTS=true` to send each JSON result to a remote endpoint instead of
printing it. The destination is specified with `RESULTS_URL` and the request will
include an `X-Auth-Token: Bearer` header using the value from `AUTH_TOKEN`.

The key service status endpoint can use TLS credentials. Provide paths and
connection details through the following environment variables. Any variable
that is not set will be omitted from the request:

* `CERT_PATH` - client certificate file
* `KEY_PATH` - client private key file
* `CACERT_PATH` - certificate authority bundle
* `PEM_PASSWORD` - password for the certificate PEM file
* `IPPORT` - hostname and port of the key management service
  
  The specific key status endpoint is built automatically from the
  configuration in `config.yaml`, so no additional path variable is needed.

## Installation

Install required Python packages:

```bash
make install
```

The agent relies on the `curl` command when contacting key services. If you run
the agent outside the provided Docker container, ensure `curl` is installed on
your system.

## Running

Set any environment variables (optionally using `.env` with `python-dotenv`) and
start the agent:

```bash
make run
```

Each iteration prints a JSON object of the form:

```json
{
  "nodes": [
    {
      "name": "example-node",
      "status": "up",
      "stored_key_count": 10,
      "current_key_rate": 1.2
    }
  ]
}
```

## Docker

To run the agent in a container, use Docker Compose:

```bash
make docker
```

The container is configured with `network_mode: host` so it shares the host's
network stack. This allows the agent to reach services bound to localhost on
the host machine.

# Copyright and license

This work has been implemented by Bogdan-Calin Ciobanu and Alin-Bogdan Popa under the supervision of prof. Pantelimon George Popescu, within the Quantum Team in the Computer Science and Engineering department,Faculty of Automatic Control and Computers, National University of Science and Technology POLITEHNICA Bucharest (C) 2024. In any type of usage of this code or released software, this notice shall be preserved without any changes.

If you use this software for research purposes, please follow the instructions in the "Cite this repository" option from the side panel.

This work has been partly supported by RoNaQCI, part of EuroQCI, DIGITAL-2021-QCI-01-DEPLOY-NATIONAL, 101091562.
