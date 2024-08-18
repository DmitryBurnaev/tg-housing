# tg-housing
Housing services' TG bot

# Install and run

## Upload config files
```shell
TARGET_SERVER="remote-server"
TARGET_DIR="/opt/tg-housing"
ssh ${TARGET_SERVER} -C  "mkdir -P ${TARGET_DIR}"
scp etc/* ${TARGET_SERVER}:${TARGET_DIR}
```

## Prepare service
```shell
TARGET_SERVER="remote-server"
TARGET_DIR="/opt/tg-housing"

ssh ${TARGET_SERVER}

# on the remote server
sudo su

# prepare user and group (NOTE: ID 1005 is imported ID for group)
groupadd --system tg-housing-srv --gid 1005
useradd --no-log-init --system --gid tg-housing-srv --uid 1005 tg-housing-srv

chown tg-housing-srv:tg-housing-srv -R /opt/tg-housing/
usermod -G docker tg-housing-srv

# copy config to systemd
ln -s ${TARGET_DIR}/tg-housing.service /etc/systemd/system/tg-housing.service
systemctl daemon-reload
systemctl enable tg-housing.service
systemctl start tg-housing.service

# see logs
journalctl -u tg-housing
```
