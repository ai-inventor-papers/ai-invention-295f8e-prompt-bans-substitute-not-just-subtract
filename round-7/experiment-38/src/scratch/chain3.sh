#!/bin/bash
cd .
while kill -0 $1 2>/dev/null; do sleep 5; done
exec scratch/chain2.sh g2smoke g2 g2r g2d
