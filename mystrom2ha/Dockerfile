FROM python:3.12.2
WORKDIR /data
COPY . /mystrom2ha
RUN /bin/chmod +x /mystrom2ha/run.sh
EXPOSE 32570/tcp
CMD ["/mystrom2ha/run.sh"]
