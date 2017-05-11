# LalkaChat [![Build Status](http://jenkins.czt.lv/job/LalkaChat/job/develop/badge/icon)](http://jenkins.czt.lv/job/LalkaChat/job/develop/)

  LalkaChat is a program for displaying multiple chats from services is one place.  
  It's cross-platform and highly configurable. You can set the style of the chat, so it can look differently and you can tweak a lot of the settings.  
  Writen in modular way so you can easily add or remove any module that you need or do not need or write your own module if you lack available functionality.  
  Uses wxPython as a GUI interface and CEF as a browser window that renders current style.  
  HTTP Server backend is using CherryPy to provide ability for modules to use REST API calls to control chat behaviour.  
  Various modules that enrich the LalkaChat functionality.  
  Supports multiple languages being English and Russian at the moment, but core is already there
  and you can translate to different languages if there is proper translations.  
  You can see how much viewers you have for each chat in the GUI (You can toggle this function on/off if you desire so).  

## Supported Websites

* [Peka2tv](http://peka2.tv/)
* [GoodGame](https://goodgame.ru/)
* [Twitch.TV](https://www.twitch.tv/)

## Architecture

LalkaChat uses conveyor architecture delivering the messages.

You configure the "Input" chat modules, such as Twitch/Goodgame and will start sending messages to the central queue 
 which will push the message to message process modules that are loaded by priority. 
Those modules each process the message and pass the message to the next module.
Last one module is WebChat module which is HTTP backend that is responsible for hosting the style/theme and sending it to browser.

## Available Modules for message processing

* Blacklist - Allows user to blacklist\hide specific words or chatters.
* Cloud2Butt - Word substitution module.
* Dwarf Fortress - Special module that picks chatters by special keyword and writes them into file.
* Levels - Adds level icons to chatter, allows them to level up in the chat and be awesome by chatting.
* Logger - Logs all the messages that come via LalkaChat pipe.
* Mentions - Allows user to specify different words to be highlighted. 
  (Example: Your username differs in different chat and you want to highlight it from everywhere)
* Webchat - Core module to allow user to view the chat from browser/GUI 

## Information for Developers
TODO
### Messaging Module Basics
TODO // Code Examples
### Chat Module Basics
TODO // Code Examples
### GUI Module Basics
TODO // Code Examples

## Installation from Source

 ToDo. Probably will be couple scripts that you can run from python.

## Installation from Package (Windows)

Unpack the zip to the folder you want, and run `LalkaChat.exe`.

## Docker Availability
Docker build is available for testing LalkaChat, uses XPRA to display GUI from browser

### Usage(GNU/Linux macOS Windows):
 - [Install docker](https://docs.docker.com/engine/installation/)
 - `docker run -d --name x11-bridge -e MODE="html" -p 10000:10000 -e XPRA_DISPLAY=:14 -e XPRA_PASSWORD=<PASSWORD> jare/x11-bridge`
 - `docker run -d --name chat -p 8080:8080 -v <PATH_TO_CONFIG>:/usr/lib/python2.7/site-packages/LalkaChat/conf deforce/lalkachat`
 - Open chat config at `http://localhost:10000/index.html?encoding=png&password=<PASSWORD>`
 - And chat window at `http://localhost:8080/`
 - You can update the chat with `docker rmi -f czt/lalkachat`
 - Remove containers with `docker rmi -f x11-bridge chat`


#### Production docker build:

 - `docker build -t deforce/alpine-wxpython:latest docker/Dockerfiles/alpine-wxpython`
 - `docker build -t deforce/lalkachat:latest .`

#### Testing docker build:
 - `docker build -t deforce/alpine-wxpython:latest docker/Dockerfiles/alpine-wxpython`
 - `docker build -t deforce/lalkachat-build-deps:latest docker/Dockerfiles/lalkachat-build-deps`
 - `docker run -d --name x11-bridge -e MODE="html" -p 10000:10000 -e XPRA_DISPLAY=:14 -e XPRA_PASSWORD=<PASSWORD> jare/x11-bridge`
 - (on source change)
  - `docker build -t deforce/lalkachat:testing -f Dockerfile_test .`
  - `docker run -rm --name chat-test -p 8080:8080 -v <PATH_TO_CONFIG>:/usr/lib/python2.7/site-packages/LalkaChat/conf deforce/lalkachat:testing`

## Special Thanks:
ftpud - for fixing IE compatibility (Old problem with IE Browser)  
JAre - for being awesome with his docker stuff  
[ichursin](https://github.com/ichursin) - for deep knowledge in JavaScript and helping me with code  
l0stparadis3 - for helping and testing in Linux environment  
