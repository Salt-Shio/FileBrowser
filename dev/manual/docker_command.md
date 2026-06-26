1. `docker-compose up --build -d`: 啟動機器
2. `docker-compose logs server`: 用來除錯
3. `docker-compose restart server`: 重啟 server
4. `docker-compose up --force-recreate -d server`: 強制重建容器以清空日誌 (Log)
5. `wsl -d docker-desktop -u root sh -c "echo -n '' > $(docker inspect --format='{{.LogPath}}' file-explorer-server)"`: 免重啟容器，直接在 Windows WSL2 環境下清空日誌檔案
6. `docker compose exec server alembic revision --autogenerate -m "修改說明"`: 【資料庫更新 Step 1】自動比對 `app/models` 與 `.db` 差異，並在 `alembic/versions` 產生一份升級草稿 (Python 檔)。此時還不會改動真實資料庫。
7. `docker compose exec server alembic upgrade head`: 【資料庫更新 Step 2】正式套用升級草稿，將最新的資料表結構變化打進 SQLite `.db` 檔案中。