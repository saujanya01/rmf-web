FROM rmf-web/builder

SHELL ["bash", "-c"]
COPY . /root/rmf-web
RUN . /opt/rmf/setup.bash && \
  npm config set unsafe-perm && \
  cd /root/rmf-web && \
  CI=1 npm run bootstrap -- packages/ros2-bridge && \
  cd packages/ros2-bridge && \
  mv $(npm pack | tail -n 1) /ros2-bridge.tgz

FROM rmf-web/builder

COPY --from=0 /ros2-bridge.tgz /

SHELL ["bash", "-c"]
RUN . /opt/rmf/setup.bash && \
  npm config set unsafe-perm && \
  npm install -g /ros2-bridge.tgz

# cleanup
RUN rm -rf /var/lib/apt/lists && \
  npm cache clean --force && \
  rm /ros2-bridge.tgz

RUN echo -e '#!/bin/bash\n\
  . /opt/rmf/setup.bash\n\
  exec ros2-bridge "$@"\n\
' > /docker-entry-point.sh && chmod +x /docker-entry-point.sh

ENTRYPOINT ["/docker-entry-point.sh"]
CMD ["--help"]
