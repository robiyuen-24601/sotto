.PHONY: run test install-agent uninstall-agent logs

PY := .venv/bin/python

run:
	$(PY) -m sotto

test:
	.venv/bin/pytest -q

install-agent:
	bash scripts/install_launch_agent.sh install

uninstall-agent:
	bash scripts/install_launch_agent.sh uninstall

logs:
	tail -f ~/Library/Logs/sotto.log
