1. `docker-compose up --build -d`: 啟動機器
2. `docker-compose logs server`: 用來除錯
3. `docker-compose restart server`: 重啟 server
4. `docker-compose up --force-recreate -d server`: 強制重建容器以清空日誌 (Log)
5. `wsl -d docker-desktop -u root sh -c "echo -n '' > $(docker inspect --format='{{.LogPath}}' file-explorer-server)"`: 免重啟容器，直接在 Windows WSL2 環境下清空日誌檔案