.PHONY: install install-all test tab image mcp clean

install:        ## base pipeline only
	pip install -e .

install-all:    ## + ADT backend, notation, agent, dev tools
	pip install -e ".[adt,notation,agent,dev]"

test:
	PYTHONPATH=. pytest -q

## tab URL=<youtube-url> — end-to-end into out/
tab:
	drumtab "$(URL)" -o out/$(shell date +%s)

image:
	podman build -t drumtab .

mcp:            ## run the MCP server (stdio) for Claude Desktop/Code
	python -m agent.mcp_server

clean:
	rm -rf runs out build *.egg-info **/__pycache__
