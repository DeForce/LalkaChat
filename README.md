# LalkaChat

## Usage(GNU/Linux macOS Windows):
 - [Install docker](https://docs.docker.com/engine/installation/)
 - `docker run -ti --rm -p 10000:10000 -p 8080:8080 -e XPRA_PASSWORD=<PASSWORD> -v <PLACE TO STORE CHAT CONFIG>:/usr/lib/python2.7/site-packages/LalkaChat/conf czt/lalkachat`
 - Open chat config at `http://localhost:10000/index.html?encoding=png&password=<PASSWORD>`
 - And chat window at `http://localhost:8080/`
 - You can update the chat with `docker rmi -f czt/lalkachat`

Thanks to ftpud for fixing IE compatibility
