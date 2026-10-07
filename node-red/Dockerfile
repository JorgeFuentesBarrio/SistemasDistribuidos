FROM nodered/node-red:latest

RUN npm install node-red-dashboard

RUN npm install node-red-contrib-web-worldmap

RUN chmod +x entrypoint.sh

CMD ["./entrypoint.sh"]