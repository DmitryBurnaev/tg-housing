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
ln -s ${TARGET_DIR}/tg-housing.service /etc/systemd/system/tg-housing.service
systemctl daemon-reload
systemctl enable tg-housing.service
systemctl start tg-housing.service
```


nano <path_to_project>/resources/tg-housing.service

# copy config to systemd
mkdir ~/.config/systemd/user/
cp <path_to_project>/resources/tg-housing.service ~/.config/systemd/user/
cd ~/.config/systemd/user/
chmod 754 . 

# reload config
systemctl --user daemon-reload

# setup new service and enable him
systemctl --user enable tg-housing.service

# run new service
systemctl --user start tg-housing.service

# check state
systemctl --user status tg-housing.service

# need reload
systemctl --user restart tg-housing.service
