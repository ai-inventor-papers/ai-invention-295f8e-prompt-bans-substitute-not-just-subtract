#!/bin/bash
cd "$(dirname "$0")/.."
until [ -f logs/chain4.done ]; do sleep 10; done
.venv/bin/python method.py s8c > logs/s8c.out 2>&1
echo done > logs/chain5.done
