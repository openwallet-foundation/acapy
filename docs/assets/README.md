# Assets Folder for Documentation

Put any assets (images, source for images, videos, etc.) in this folder to be referenced in the various documents for this repo.

## Plantuml Source and Images

Plantuml diagrams are stored in this folder in source form in files ending in `.puml` and are generated manually using the `./genPlantuml` script. The script uses a docker image from docker-hub and can be run without downloading any dependencies.

If you don't want to use the script, download plantuml and a command line utility and use that for the plantuml generation. I preferred not having any dependencies used (other than docker) and couldn't find
a nice way to run plantuml headless from a command line.

## To Do

It would be better to use a local `Dockerfile` vs. one found on Docker Hub. The one I did find was simple and straight forward.

I couldn't tell if the svg generation was working so just went with png. Not sure which would be better.