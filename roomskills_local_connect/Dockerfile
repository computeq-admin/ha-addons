FROM python:3.12.2
WORKDIR /data
COPY run.sh /opt/rlc_init.sh
RUN chmod a+x /opt/rlc_init.sh
CMD [ "/opt/rlc_init.sh" ]
EXPOSE 32653/tcp
EXPOSE 32655/tcp
EXPOSE 32656/tcp
