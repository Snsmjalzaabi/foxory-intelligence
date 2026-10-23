import {defineConfig} from '@playwright/test';
export default defineConfig({testDir:'./tests',workers:1,timeout:120000,expect:{timeout:20000},use:{baseURL:'http://localhost:8001',headless:true},webServer:{command:'../.venv/bin/python ../scripts/e2e_server.py',url:'http://localhost:8001/api/health',reuseExistingServer:false,timeout:120000}});
