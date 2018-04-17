#!/bin/bash

if ! [ -x "$(command -v docker)" ]; then
    ctx logger info "Error: docker is not installed. Maybe it is still downloading."
    exit 1
fi

cd $HOME
mkdir $HOME/wordpress && cd $HOME/wordpress
DEBUGLOG=$HOME/wordpress/debug

ctx logger info "Downloading and running Docker images."

{
    sudo docker pull mariadb:latest
    sudo docker pull wordpress
    sudo docker run -e MYSQL_ROOT_PASSWORD=SenorPassword -e MYSQL_DATABASE=wordpress --name wordpressdb -v "$PWD/database":/var/lib/mysql -d mariadb:latest
    sudo docker run -e WORDPRESS_DB_PASSWORD=SenorPassword --name wordpress --link wordpressdb:mysql -p 80:80 -v "$PWD/html":/var/www/html -d wordpress
} 2>&1 | tee -a $DEBUGLOG
OUTPUT=$(cat $DEBUGLOG)
ctx logger info "${OUTPUT}"
