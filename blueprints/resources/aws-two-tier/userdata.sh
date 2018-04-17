#!/bin/bash -v

sudo usermod -aG docker ubuntu
sudo apt-get install curl
curl -fsSL https://get.docker.com/ | sh
